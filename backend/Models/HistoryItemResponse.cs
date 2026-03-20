namespace MisinformationRiskAssessment.Api.Models;

public sealed class HistoryItemResponse
{
    public Guid Id { get; set; }
    public string Title { get; set; } = string.Empty;
    public string RiskLevel { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string Explanation { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}
