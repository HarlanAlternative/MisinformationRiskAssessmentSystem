namespace MisinformationRiskAssessment.Api.Models;

public sealed class FeatureSignals
{
    public int TextLength { get; set; }
    public int WordCount { get; set; }
    public int PunctuationCount { get; set; }
    public double EmotionalWordRatio { get; set; }
    public double UppercaseRatio { get; set; }
    public int ExclamationCount { get; set; }
    public int ExaggerationCount { get; set; }
    public bool HasSource { get; set; }
    public List<string> TopKeywords { get; set; } = [];
    public List<string> TransformerTokens { get; set; } = [];
    public Dictionary<string, double> ModelScores { get; set; } = [];
}
