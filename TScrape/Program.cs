using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using HtmlAgilityPack;
using Nest;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Console;
using Microsoft.Extensions.Logging.Debug;

public class Product
{
    public string ProductName { get; set; }
}

public class Program
{
    private static ElasticClient CreateElasticClient()
    {
        // Elasticsearch bağlantı ayarlarını yapılandırır ve bir ElasticClient döndürür.
        var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
            .DefaultIndex("wee");
        return new ElasticClient(settings);
    }

    private static async Task<List<Product>> ScrapeTrendyolAsync()
    {
        var url = "https://www.trendyol.com/gezer/erkek-siyah-beyaz-rahat-taban-lux-banyo-havuz-plaj-terlik-p-99258600?boutiqueId=61&merchantId=141253&sav=true";
        var httpClient = new HttpClient();
        var html = await httpClient.GetStringAsync(url);

        var htmlDocument = new HtmlDocument();
        htmlDocument.LoadHtml(html);

        var productNodes = htmlDocument.DocumentNode.SelectNodes("//h1[@class='pr-new-br']");
        var products = new List<Product>();

        if (productNodes != null)
        {
            foreach (var node in productNodes)
            {
                var titleNode = node.SelectSingleNode(".//a[@class='product-brand-name-with-link']");
                var titleSpan = node.SelectSingleNode(".//span");

                if (titleNode != null && titleSpan != null)
                {
                    var product = new Product
                    {
                        ProductName = $"{titleNode.InnerText.Trim()} {titleSpan.InnerText.Trim()}"
                    };
                    products.Add(product);
                }
            }
        }

        return products;
    }

    private static void IndexProducts(ElasticClient client, List<Product> products, ILogger logger)
    {
        // Elasticsearch'e ürünleri indeksler.
        foreach (var product in products)
        {
            var response = client.IndexDocument(product);
            if (!response.IsValid)
            {
                logger.LogError($"Error indexing product: {product.ProductName}, Reason: {response.ServerError}");
            }
        }
    }

    private static void CreateIndexIfNotExists(ElasticClient client, ILogger logger)
    {
        // Elasticsearch'te indexin var olup olmadığını kontrol eder, yoksa oluşturur.
        var indexExistsResponse = client.Indices.Exists("products");
        if (!indexExistsResponse.Exists)
        {
            var createIndexResponse = client.Indices.Create("products", c => c
                .Map<Product>(m => m.AutoMap())
            );

            if (!createIndexResponse.IsValid)
            {
                logger.LogError("Error creating index: {Reason}", createIndexResponse.ServerError);
            }
        }
    }

    private static void SearchProducts(ElasticClient client, string searchText, ILogger logger)
    {
        // Verilen metinle eşleşen ürünleri Elasticsearch'te arar.
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
        int counter = 0; // 
        int x = 5; // çıktıda gösterilecek sonuç sayısı
        foreach (var product in searchResponse.Documents)
        {
            if (counter >= x) { break; } // En fazla x ürünü yazdırması için.
            Console.WriteLine($"Product: {product.ProductName}\n--------------------------------------------");
            counter++;
        }
        Console.WriteLine(searchResponse.Documents.Count + " matchup");
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

        Stopwatch stopwatch = new Stopwatch(); // Zamanlayıcı oluşturur

        var client = CreateElasticClient(); // Elasticsearch istemcisini oluşturur

        CreateIndexIfNotExists(client, logger); // Elasticsearch'te index varsa kontrol eder, yoksa oluşturur

        var products = await ScrapeTrendyolAsync(); // Trendyol web sitesinden ürünleri çeker
        IndexProducts(client, products, logger); // Çekilen ürünleri Elasticsearch'e indeksler

        stopwatch.Start();
        SearchProducts(client, "icecek", logger); // Elasticsearch'te girilen kelimeyi arar
        stopwatch.Stop();

        Console.WriteLine($"Search completed in {stopwatch.ElapsedMilliseconds} ms.");
    }
}
