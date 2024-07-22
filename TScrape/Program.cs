using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using HtmlAgilityPack;
using Nest;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Console;
using Microsoft.Extensions.Logging.Debug;
using System.Diagnostics;

public class Product // Info about product
{
    public string? ProductName { get; set; }
    public List<string>? Prices { get; set; } // TL
    public List<string>? Quantities { get; set; } // gram
}

public class Program
{
    private static ElasticClient CreateElasticClient()
    {
        // Elasticsearch bağlantı ayarlarını yapılandırır ve bir ElasticClient döndürür.
        var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
            .DefaultIndex("cumbakuruyemish");
        return new ElasticClient(settings);
    }

    private static async Task<List<Product>> ScrapeWebAsync()
    {
        var url = "https://cumbakuruyemis.com/Kategori"; // Website we pull data -------------------------------
        var httpClient = new HttpClient();
        var products = new List<Product>();

        try
        {
            var html = await httpClient.GetStringAsync(url);

            var htmlDocument = new HtmlDocument();
            htmlDocument.LoadHtml(html);

            var productNodes = htmlDocument.DocumentNode.SelectNodes("//div[contains(@class, 'col-xl-4 col-lg-6 col-md-6 mt-4')]");

            if (productNodes != null)
            {
                foreach (var node in productNodes)
                {
                    var productNameNode = node.SelectSingleNode(".//a[@class='text-decoration-none textBlack']");
                    var priceNodes = node.SelectNodes(".//div[contains(@class, 'newPrice')]");
                    var quantityNodes = node.SelectNodes(".//span[contains(@class, 'productQuantityText')]");

                    var prices = new List<string>();
                    if (priceNodes != null)
                    {
                        foreach (var priceNode in priceNodes)
                        {
                            prices.Add(priceNode.InnerText.Trim());
                        }
                    }

                    var quantities = new List<string>();
                    if (quantityNodes != null)
                    {
                        foreach (var quantityNode in quantityNodes)
                        {
                            quantities.Add(quantityNode.InnerText.Trim());
                        }
                    }

                    var product = new Product
                    {
                        ProductName = productNameNode?.InnerText.Trim(),
                        Prices = prices,
                        Quantities = quantities
                    };

                    products.Add(product);
                }
            }
        }
        catch (HttpRequestException e)
        {
            Console.WriteLine($"Request error: {e.Message}");
        }
        catch (Exception e)
        {
            Console.WriteLine($"An error occurred: {e.Message}");
        }

        return products;
    }

    private static void IndexProducts(ElasticClient client, List<Product> products, ILogger logger)
    {
        // Elasticsearch'e ürünleri indeksler.
        foreach (var product in products)
        {
            var response = client.IndexDocument(product);
        }
    }

    private static void CreateIndexIfNotExists(ElasticClient client, ILogger logger) // Elasticsearch'te indexin var olup olmadığını kontrol eder, yoksa oluşturur.
    {
        var indexExistsResponse = client.Indices.Exists("cumbakuruyemish");
        if (!indexExistsResponse.Exists)
        {
            var createIndexResponse = client.Indices.Create("cumbakuruyemish", c => c
                .Map<Product>(m => m.AutoMap())
            );

            if (!createIndexResponse.IsValid)
            {
                logger.LogError("Error creating index: {Reason}", createIndexResponse.ServerError);
            }
        }
    }

    private static void SearchProducts(ElasticClient client, string searchText, ILogger logger) // Verilen metinle eşleşen ürünleri Elasticsearch'te arar.
    {
        var searchResponse = client.Search<Product>(s => s
            .Query(q => q
                .MultiMatch(mm => mm
                    .Query(searchText)
                    .Fields(f => f
                        .Field(p => p.ProductName, 3.0) // Ürün adına ağırlık verir.
                    )
                    .Fuzziness(Fuzziness.Auto) // Otomatik bulanıklık ayarı.
                )
            )
            .Sort(srt => srt
                .Descending(SortSpecialField.Score) // Sonuçları puan sırasına göre sıralar.
            )
        );

        if (!searchResponse.IsValid)
        {
            logger.LogError("Error searching products: {Reason}", searchResponse.ServerError);
            return;
        }

        Console.WriteLine("Results:\n--------------------------------------------");
        int counter = 0;
        int x = 10; // çıktıda gösterilecek sonuç sayısı
        foreach (var product in searchResponse.Documents)
        {
            if (counter >= x) { break; } // En fazla x ürünü yazdırması için.
            Console.WriteLine($"Product: {product.ProductName}");
            if (product.Prices != null)
            {
                foreach (var price in product.Prices)
                {
                    Console.WriteLine($"Price: {price}");
                }
            }
            if (product.Quantities != null) // printing quantity info
            {
                foreach (var quantity in product.Quantities)
                {
                    Console.WriteLine($"Quantity: {quantity}");
                }
            }
            Console.WriteLine("--------------------------------------------");
            counter++;
        }
        Console.WriteLine(searchResponse.Documents.Count + " match(es).");
    }

    public static async Task Main(string[] args)
    {
        // Logger kurulumu
        using var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.AddConsole();
            builder.AddDebug();
        });
        var logger = loggerFactory.CreateLogger<Program>();

        Stopwatch stopwatch1 = new Stopwatch(); // Zamanlayıcı oluşturur
        Stopwatch stopwatch2 = new Stopwatch(); 
        stopwatch2.Start();
        var client = CreateElasticClient(); // Elasticsearch istemcisini oluşturur

        CreateIndexIfNotExists(client, logger); // Elasticsearch'te index varsa kontrol eder, yoksa oluşturur

        var products = await ScrapeWebAsync(); // Web sitesinden ürünleri çeker
        
        const string flagFilePath = "flags/indexing_done_26.flag"; // Dosya oluşturmak için
        
        if (!File.Exists(flagFilePath)) // Dosyanın oluşturulup oluşturulmadığını kontrol eder
        {   
            IndexProducts(client, products, logger); // Çekilen ürünleri Elasticsearch'e indeksler
            File.Create(flagFilePath).Dispose(); // Dosya oluşturularak indekslemenin yapıldığını işaretler
        } 

        var item = "badem" ; // user input ----------------------------------------------------------------
        
        stopwatch1.Start();
        SearchProducts(client, item, logger); // Elasticsearch'te girilen kelimeyi arar
        stopwatch1.Stop();
        stopwatch2.Stop();

        Console.WriteLine($"Search completed in {stopwatch1.ElapsedMilliseconds} ms.");
        Console.WriteLine($"All completed in {stopwatch2.ElapsedMilliseconds} ms.");
    }
}