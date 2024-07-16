using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using HtmlAgilityPack;
using Nest;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Console;
using Microsoft.Extensions.Logging.Debug;
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using System.IO;

public class Product
{
    public string? ProductName { get; set; }
}

public class Program
{
    private static ElasticClient CreateElasticClient()
    {
        var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
            .DefaultIndex("weeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee");
        return new ElasticClient(settings);
    }

    private static List<Product> ScrapeProductsFromPage(IWebDriver driver)
    {
        var products = new List<Product>();

        var html = driver.PageSource;
        var htmlDocument = new HtmlDocument();
        htmlDocument.LoadHtml(html);

        var productNodes = htmlDocument.DocumentNode.SelectNodes("//a[@class='text-decoration-none textBlack']");

        if (productNodes != null)
        {
            foreach (var node in productNodes)
            {
                var product = new Product
                {
                    ProductName = node.InnerText.Trim()
                };
                products.Add(product);
            }
        }

        return products;
    }

    private static async Task<List<Product>> ScrapeAllPagesAsync()
    {
        var allProducts = new List<Product>();

        var options = new ChromeOptions();
        options.AddArgument("--headless"); // Tarayıcıyı arka planda çalıştırır
        using (var driver = new ChromeDriver(options))
        {
            driver.Navigate().GoToUrl("https://cumbakuruyemis.com/Kategori");

            var wait = new WebDriverWait(driver, TimeSpan.FromSeconds(10));
            wait.Until(d => d.FindElement(By.ClassName("categoryNavigationButtons")));

            for (int pageNumber = 1; pageNumber <= 19; pageNumber++)
            {
                if (pageNumber > 1)
                {
                    var nextPageButton = driver.FindElement(By.XPath($"//a[@onclick='updatePage({pageNumber})']"));
                    nextPageButton.Click();

                    wait.Until(d => d.FindElement(By.ClassName("categoryNavigationButtons")));
                }

                var products = ScrapeProductsFromPage(driver);
                allProducts.AddRange(products);
            }
        }

        return allProducts;
    }

    private static void IndexProducts(ElasticClient client, List<Product> products, ILogger logger)
    {
        foreach (var product in products)
        {
            var response = client.IndexDocument(product);
        }
    }

    private static void CreateIndexIfNotExists(ElasticClient client, ILogger logger)
    {
        var indexExistsResponse = client.Indices.Exists("weeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee");
        if (!indexExistsResponse.Exists)
        {
            var createIndexResponse = client.Indices.Create("weeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", c => c
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
        var searchResponse = client.Search<Product>(s => s
            .Query(q => q
                .MultiMatch(mm => mm
                    .Query(searchText)
                    .Fields(f => f
                        .Field(p => p.ProductName, 3.0)
                    )
                    .Fuzziness(Fuzziness.Auto)
                )
            )
            .Sort(srt => srt
                .Descending(SortSpecialField.Score)
            )
        );

        if (!searchResponse.IsValid)
        {
            logger.LogError("Error searching products: {Reason}", searchResponse.ServerError);
            return;
        }

        Console.WriteLine("Results:\n--------------------------------------------");
        int counter = 0;
        int x = 10;
        foreach (var product in searchResponse.Documents)
        {
            if (counter >= x) { break; }
            Console.WriteLine($"Product: {product.ProductName}\n--------------------------------------------");
            counter++;
        }
        Console.WriteLine(searchResponse.Documents.Count + " matchup");
    }

    public static async Task Main(string[] args)
    {
        using var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder.AddConsole();
            builder.AddDebug();
        });
        var logger = loggerFactory.CreateLogger<Program>();

        var client = CreateElasticClient();

        CreateIndexIfNotExists(client, logger);

        var products = await ScrapeAllPagesAsync();

        const string flagFilePath = "flags/indexing_done9.flag";

        if (!File.Exists(flagFilePath))
        {
            IndexProducts(client, products, logger);
            File.Create(flagFilePath).Dispose();
        }
        else { logger.LogInformation("Products have already been indexed."); }

        var stopwatch = new System.Diagnostics.Stopwatch();
        stopwatch.Start();
        SearchProducts(client, "TARZAN", logger);
        stopwatch.Stop();

        Console.WriteLine($"Search completed in {stopwatch.ElapsedMilliseconds} ms.");
    }
}
