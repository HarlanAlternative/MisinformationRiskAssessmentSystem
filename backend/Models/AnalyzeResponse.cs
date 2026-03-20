namespace MisinformationRiskAssessment.Api.Models;

public sealed class AnalyzeResponse
{
    public Guid Id { get; set; }
    public string RiskLevel { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string Explanation { get; set; } = string.Empty;
    public FeatureSignals FeatureSignals { get; set; } = new();
    public DateTime CreatedAt { get; set; }
}
