namespace MisinformationRiskAssessment.Api.Models;

public sealed class AnalysisRecordResponse
{
    public Guid Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string? Content { get; set; }
    public string? Source { get; set; }
    public string RiskLevel { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string Explanation { get; set; } = string.Empty;
    public FeatureSignals FeatureSignals { get; set; } = new();
    public DateTime CreatedAt { get; set; }
}
