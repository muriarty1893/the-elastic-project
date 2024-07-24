using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using HtmlAgilityPack;
using Nest;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;

namespace ProductScraper
{
    public class Product
    {
        public string? ProductName { get; set; }
        public List<float>? Prices { get; set; }
        public string? RatingCount { get; set; }
        public Dictionary<string, string>? Attributes { get; set; }

        public Product()
        {
            Prices = new List<float>();
            Attributes = new Dictionary<string, string>();
        }
    }

    class Program
    {
        private static readonly string IndexName = "indext11";
        private static readonly string FlagName = "flags/indexing_done_63.flag";

        static async Task Main(string[] args)
        {
            var services = new ServiceCollection()
                .AddLogging(configure => configure.AddConsole())
                .AddSingleton<HttpClient>()
                .AddSingleton(CreateElasticClient())
                .BuildServiceProvider();

            var logger = services.GetRequiredService<ILogger<Program>>();
            var client = services.GetRequiredService<ElasticClient>();
            var httpClient = services.GetRequiredService<HttpClient>();

            await CreateIndexIfNotExists(client, logger);

            var products = await ScrapeWeb(httpClient, logger);

            if (!File.Exists(FlagName))
            {
                await IndexProducts(client, products, logger);

                Directory.CreateDirectory(Path.GetDirectoryName(FlagName));
                await File.WriteAllTextAsync(FlagName, "");
            }

            string item = "steelseries"; // User input
            
            if (File.Exists(FlagName))
            {
                await SearchProducts(client, item, logger);
            }
        }

        private static ElasticClient CreateElasticClient()
        {
            var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
                .DefaultIndex(IndexName);
            return new ElasticClient(settings);
        }

        private static async Task<List<Product>> ScrapeWeb(HttpClient httpClient, ILogger logger)
        {
            var url = "https://www.trendyol.com/sr/oyuncu-mouselari-x-c106088?sst=BEST_SELLER";
            var products = new List<Product>();

            try
            {
                var response = await httpClient.GetAsync(url);

                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var htmlDoc = new HtmlDocument();
                    htmlDoc.LoadHtml(content);
                    var productNodes = htmlDoc.DocumentNode.SelectNodes("//div[contains(@class, 'p-card-chldrn-cntnr card-border')]");

                    foreach (var node in productNodes)
                    {
                        var productNameNode = node.SelectSingleNode(".//h3[contains(@class, 'prdct-desc-cntnr-ttl-w')]");
                        var priceNode = node.SelectSingleNode(".//div[contains(@class, 'prc-box-dscntd')]");
                        var ratingCountNode = node.SelectSingleNode(".//span[contains(@class, 'ratingCount')]");
                        var productLinkNode = node.SelectSingleNode(".//a");

                        var productName = string.Join(" ", new[]
                        {
                            productNameNode?.SelectSingleNode(".//span[contains(@class, 'prdct-desc-cntnr-ttl')]")?.InnerText.Trim(),
                            productNameNode?.SelectSingleNode(".//span[contains(@class, 'prdct-desc-cntnr-name')]")?.InnerText.Trim(),
                            productNameNode?.SelectSingleNode(".//div[contains(@class, 'product-desc-sub-text')]")?.InnerText.Trim()
                        }).Trim();

                        var price = priceNode != null ? float.Parse(priceNode.InnerText.Replace("TL", "").Replace(",", "").Replace(".", "").Trim()) : (float?)null;
                        var ratingCount = ratingCountNode?.InnerText.Trim();
                        var productLink = productLinkNode != null ? $"https://www.trendyol.com{productLinkNode.GetAttributeValue("href", "")}" : null;

                        var attributes = !string.IsNullOrEmpty(productLink) ? await ScrapeProductDetails(httpClient, productLink, logger) : new Dictionary<string, string>();

                        var product = new Product
                        {
                            ProductName = productName,
                            Prices = price.HasValue ? new List<float> { price.Value } : new List<float>(),
                            RatingCount = ratingCount,
                            Attributes = attributes
                        };

                        products.Add(product);
                    }
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while scraping the web.");
            }

            return products;
        }

        private static async Task<Dictionary<string, string>> ScrapeProductDetails(HttpClient httpClient, string url, ILogger logger)
        {
            var attributes = new Dictionary<string, string>();

            try
            {
                var response = await httpClient.GetAsync(url);

                if (response.IsSuccessStatusCode)
                {
                    var content = await response.Content.ReadAsStringAsync();
                    var htmlDoc = new HtmlDocument();
                    htmlDoc.LoadHtml(content);

                    var attributeMappings = new Dictionary<string, string>
                    {
                        { "Mouse Hassasiyeti (Dpi)", "dpi" },
                        { "RGB Aydınlatma", "rgb_lighting" },
                        { "Mouse Tipi", "mouse_type" },
                        { "Buton Sayısı", "button_count" }
                    };

                    foreach (var mapping in attributeMappings)
                    {
                        var attrNode = htmlDoc.DocumentNode.SelectSingleNode($"//span[@title='{mapping.Key}']/following-sibling::span[@class='attribute-value']/div[contains(@class, 'attr-name')]");
                        attributes[mapping.Value] = attrNode?.InnerText.Trim();
                    }
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while scraping product details.");
            }

            return attributes;
        }

        private static async Task IndexProducts(ElasticClient client, List<Product> products, ILogger logger)
        {
            try
            {
                var bulkDescriptor = new BulkDescriptor();

                foreach (var product in products)
                {
                    bulkDescriptor.Index<Product>(op => op
                        .Index(IndexName)
                        .Document(product));
                }

                await client.BulkAsync(bulkDescriptor);
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while indexing products.");
            }
        }

        private static async Task CreateIndexIfNotExists(ElasticClient client, ILogger logger)
        {
            try
            {
                var existsResponse = await client.Indices.ExistsAsync(IndexName);
                if (!existsResponse.Exists)
                {
                    await client.Indices.CreateAsync(IndexName, c => c
                        .Map<Product>(m => m
                            .Properties(p => p
                                .Text(t => t.Name(n => n.ProductName))
                                .Number(n => n.Name(n => n.Prices).Type(NumberType.Float))
                                .Keyword(k => k.Name(n => n.RatingCount))
                                .Object<Dictionary<string, string>>(o => o.Name(n => n.Attributes).Enabled(false))
                            )
                        )
                    );
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while creating the index.");
            }
        }

        private static async Task SearchProducts(ElasticClient client, string searchText, ILogger logger)
        {
            try
            {
                var searchResponse = await client.SearchAsync<Product>(s => s
                    .Index(IndexName)
                    .Query(q => q
                        .Bool(b => b
                            .Must(mu => mu
                                .MultiMatch(mm => mm
                                    .Query(searchText)
                                    .Fields(f => f
                                        .Field(p => p.ProductName, boost: 3)
                                        .Field(p => p.RatingCount)
                                    )
                                    .Fuzziness(Fuzziness.Auto)
                                ),
                                mu => mu
                                .Range(r => r
                                    .Field(p => p.Prices)
                                    .GreaterThanOrEquals(0)
                                )
                            )
                        )
                    )
                    .Aggregations(a => a
                        .Range("price_ranges", r => r
                            .Field(p => p.Prices)
                            .Ranges(
                                r => r.To(50),
                                r => r.From(50).To(1000),
                                r => r.From(1000)
                            )
                        )
                    )
                );

                var results = searchResponse.Hits;
                Console.WriteLine($"\n\n{results.Count} match(es):");
                Console.WriteLine("Results:\n--------------------------------------------");
                foreach (var result in results)
                {
                    var product = result.Source;
                    Console.WriteLine($"Product: {product.ProductName}");
                    foreach (var price in product.Prices)
                    {
                        Console.WriteLine($"Price: {price}");
                    }
                    int carry = int.Parse(product.RatingCount.Replace("(", "").Replace(")", ""));
                    if (carry < 100)
                    {
                        Console.WriteLine($"Rating Count: {product.RatingCount} warning! number of rate is below 100");
                    }
                    else
                    {
                        Console.WriteLine($"Rating Count: {product.RatingCount}");
                    }
                    Console.WriteLine("--------------------------------------------");
                }

                var priceRanges = searchResponse.Aggregations.Range("price_ranges");
                Console.WriteLine("Aggregation Results:\n--------------------------------------------");
                foreach (var bucket in priceRanges.Buckets)
                {
                    Console.WriteLine($"Price range: {bucket.Key} - Doc count: {bucket.DocCount}");
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "An error occurred while searching products.");
            }
        }
    }
}
