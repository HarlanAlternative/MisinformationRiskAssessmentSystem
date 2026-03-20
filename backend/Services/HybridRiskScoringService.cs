using Microsoft.Extensions.Options;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class HybridRiskScoringService(
    IOptions<MachineLearningOptions> options) : IHybridRiskScoringService
{
    private readonly MachineLearningOptions _options = options.Value;

    private static readonly string[] TrustedSources =
    [
        "ap", "associated press", "bbc", "ft", "guardian", "nytimes", "reuters", "wsj"
    ];

    public RiskAssessment Evaluate(
        AnalyzeRequest request,
        FeatureSignals featureSignals,
        ClassicalPredictionResult classicalPrediction,
        BertPredictionResult bertPrediction)
    {
        var weightedScore =
            (0.5 * classicalPrediction.LogisticScore) +
            (0.3 * classicalPrediction.RandomForestScore) +
            (0.2 * bertPrediction.Score);

        var adjustment = 0d;
        var explanationFragments = new List<string>();

        if (!featureSignals.HasSource)
        {
            adjustment += 0.05;
            explanationFragments.Add("lacks a named source");
        }

        if (featureSignals.EmotionalWordRatio >= 0.03)
        {
            adjustment += 0.04;
            explanationFragments.Add("shows high emotional intensity");
        }

        if (featureSignals.UppercaseRatio >= 0.12)
        {
            adjustment += 0.03;
            explanationFragments.Add("uses an unusual amount of uppercase language");
        }

        if (featureSignals.ExclamationCount >= 2)
        {
            adjustment += 0.03;
            explanationFragments.Add("relies on emphatic punctuation");
        }

        if (featureSignals.ExaggerationCount > 0)
        {
            adjustment += Math.Min(0.05, featureSignals.ExaggerationCount * 0.015);
            explanationFragments.Add("contains exaggeration cues");
        }

        if (featureSignals.WordCount < 35)
        {
            adjustment += 0.03;
            explanationFragments.Add("offers limited context");
        }

        if (featureSignals.HasSource && LooksTrusted(request.Source))
        {
            adjustment -= 0.03;
            explanationFragments.Add("includes a source pattern seen in established outlets");
        }

        var finalScore = Math.Clamp(weightedScore + adjustment, 0, 1);
        var riskLevel = finalScore >= _options.HighRiskThreshold
            ? "High"
            : finalScore >= _options.MediumRiskThreshold
                ? "Medium"
                : "Low";

        var modelScores = new Dictionary<string, double>
        {
            ["logisticRegression"] = Math.Round(classicalPrediction.LogisticScore, 4),
            ["randomForest"] = Math.Round(classicalPrediction.RandomForestScore, 4),
            ["bert"] = Math.Round(bertPrediction.Score, 4),
            ["hybrid"] = Math.Round(finalScore, 4)
        };

        var topTerms = classicalPrediction.TopTerms
            .Where(term => !string.IsNullOrWhiteSpace(term))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(5)
            .ToList();

        var salientTokens = bertPrediction.SalientTokens
            .Where(token => !string.IsNullOrWhiteSpace(token))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(5)
            .ToList();

        return new RiskAssessment
        {
            RiskLevel = riskLevel,
            ConfidenceScore = Math.Round(finalScore, 4),
            Explanation = BuildExplanation(riskLevel, finalScore, explanationFragments, topTerms, salientTokens),
            ModelScores = modelScores,
            TopKeywords = topTerms,
            TransformerTokens = salientTokens
        };
    }

    private static bool LooksTrusted(string? source)
    {
        if (string.IsNullOrWhiteSpace(source))
        {
            return false;
        }

        return TrustedSources.Any(candidate => source.Contains(candidate, StringComparison.OrdinalIgnoreCase));
    }

    private static string BuildExplanation(
        string riskLevel,
        double finalScore,
        IEnumerable<string> explanationFragments,
        IReadOnlyCollection<string> topTerms,
        IReadOnlyCollection<string> salientTokens)
    {
        var sentences = new List<string>
        {
            $"The claim is assessed as {riskLevel.ToLowerInvariant()} risk with a weighted misinformation score of {finalScore:0.00}."
        };

        var fragments = explanationFragments.ToList();
        if (fragments.Count > 0)
        {
            sentences.Add($"It {string.Join(", ", fragments)}.");
        }

        if (topTerms.Count > 0)
        {
            sentences.Add($"Key lexical signals include {string.Join(", ", topTerms.Take(3))}.");
        }

        if (salientTokens.Count > 0)
        {
            sentences.Add($"The transformer model focused on {string.Join(", ", salientTokens.Take(3))}.");
        }

        return string.Join(" ", sentences);
    }
}
