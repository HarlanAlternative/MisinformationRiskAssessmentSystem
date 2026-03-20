namespace MisinformationRiskAssessment.Api.Models;

public sealed class ClassicalPredictionResult
{
    public double LogisticScore { get; set; }
    public double RandomForestScore { get; set; }
    public List<string> TopTerms { get; set; } = [];
}
