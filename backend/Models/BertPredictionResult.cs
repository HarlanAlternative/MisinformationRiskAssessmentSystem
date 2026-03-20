namespace MisinformationRiskAssessment.Api.Models;

public sealed class BertPredictionResult
{
    public double Score { get; set; }
    public string Label { get; set; } = string.Empty;
    public List<string> SalientTokens { get; set; } = [];
}
