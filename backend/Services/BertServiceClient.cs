using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Options;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class BertServiceClient(
    HttpClient httpClient,
    IOptions<BertServiceOptions> options) : IBertServiceClient
{
    private readonly HttpClient _httpClient = httpClient;
    private readonly BertServiceOptions _options = options.Value;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<BertPredictionResult> PredictAsync(AnalyzeRequest request, CancellationToken cancellationToken)
    {
        EnsureBaseAddress();

        using var response = await _httpClient.PostAsJsonAsync("/predict", request, JsonOptions, cancellationToken);
        response.EnsureSuccessStatusCode();

        var prediction = await response.Content.ReadFromJsonAsync<BertPredictionResult>(JsonOptions, cancellationToken);
        return prediction ?? throw new InvalidOperationException("BERT service returned an empty response.");
    }

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken)
    {
        try
        {
            EnsureBaseAddress();
            using var response = await _httpClient.GetAsync("/health", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private void EnsureBaseAddress()
    {
        if (_httpClient.BaseAddress is not null)
        {
            return;
        }

        _httpClient.BaseAddress = new Uri(_options.Url.TrimEnd('/'));
    }
}
