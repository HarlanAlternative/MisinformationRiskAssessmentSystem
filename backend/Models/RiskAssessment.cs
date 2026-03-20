namespace MisinformationRiskAssessment.Api.Models;

public sealed class RiskAssessment
{
    public string RiskLevel { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string Explanation { get; set; } = string.Empty;
    public Dictionary<string, double> ModelScores { get; set; } = [];
    public List<string> TopKeywords { get; set; } = [];
    public List<string> TransformerTokens { get; set; } = [];
}
