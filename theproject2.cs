using System;
using System.Collections.Generic;
using System.Net.Http;
using HtmlAgilityPack;
using Nest;

// Bu sınıf ürün bilgilerini tutmak için kullanılır
public class Product
{
    public string Title { get; set; }
    public string Description { get; set; }
}

public class Program
{
    static async System.Threading.Tasks.Task Main(string[] args)
    {
        // Elasticsearch bağlantısı için gerekli ayarlar
        var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
            .DefaultIndex("trendyol1"); // Varsayılan indeks ismi 'products' olarak ayarlandı

        var client = new ElasticClient(settings);

        // Web scraping için kullanacağımız URL
        var url = "https://www.trendyol.com/hc-care/complex-bitkisel-sac-bakim-kompleksi-100-ml-p-7103578?boutiqueId=61&merchantId=110268&sav=true"; // Örnek olarak Trendyol ana sayfası

        var httpClient = new HttpClient();
        var html = await httpClient.GetStringAsync(url);

        // HtmlAgilityPack kullanarak HTML belgesini yükle
        var htmlDocument = new HtmlDocument();
        htmlDocument.LoadHtml(html);

        // HTML belgesinde istediğimiz verileri seçmek için XPath veya CSS seçicilerini kullanın
        // Bu örnekte, ürün başlıklarını ve açıklamalarını çekiyoruz
        var productNodes = htmlDocument.DocumentNode.SelectNodes("//h1[@class='pr-new-br']");

        var products = new List<Product>();

        foreach (var node in productNodes)
        {
            var titleNode = node.SelectSingleNode(".//a[@class='product-brand-name-with-link']");
            var titleSpan = node.SelectSingleNode(".//span");

            if (titleNode != null && titleSpan != null)
            {
                // Ürün açıklamalarını bulmak için ilgili bölümdeki XPath ifadesi
                var descriptionNode = htmlDocument.DocumentNode.SelectSingleNode("//div[@id='marketing-product-detail-seo-content']//div[@class='product-detail-seo-content']//div[@class='seo-content-wrapper']//div[@class='seo-content']//section//div//div//p");

                var product = new Product
                {
                    Title = $"{titleNode.InnerText.Trim()} {titleSpan.InnerText.Trim()}",
                    Description = descriptionNode?.InnerText.Trim()
                };

                products.Add(product);
            }
        }

        // Çekilen verileri Elasticsearch'e indekslemek için
        var indexResponse = client.IndexMany(products);

        if (indexResponse.Errors)
        {
            Console.WriteLine("Bazı veriler indekslenirken hata oluştu.");
        }
        else
        {
            Console.WriteLine("Veriler başarıyla indekslendi.");
        }
    }
}
