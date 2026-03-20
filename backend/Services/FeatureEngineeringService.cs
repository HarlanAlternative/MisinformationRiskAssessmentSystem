using System.Text.RegularExpressions;
using MisinformationRiskAssessment.Api.Models;

namespace MisinformationRiskAssessment.Api.Services;

public sealed class FeatureEngineeringService : IFeatureEngineeringService
{
    private static readonly Regex WordRegex = new(@"\b[\p{L}\p{N}'-]+\b", RegexOptions.Compiled);

    private static readonly HashSet<string> EmotionalWords =
    [
        "amazing", "angry", "astonishing", "bombshell", "breaking", "crisis", "danger",
        "disaster", "fear", "furious", "hate", "incredible", "massive", "miracle",
        "panic", "rage", "scandal", "secret", "shocking", "terrifying", "urgent"
    ];

    private static readonly HashSet<string> ExaggerationWords =
    [
        "always", "completely", "everyone", "guaranteed", "must-see", "never",
        "nobody", "proof", "totally", "unbelievable", "undeniable"
    ];

    public FeatureSignals Extract(string title, string? content, string? source)
    {
        var combinedText = $"{title} {content}".Trim();
        var words = WordRegex.Matches(combinedText)
            .Select(match => match.Value)
            .Where(value => !string.IsNullOrWhiteSpace(value))
            .ToArray();

        var totalLetters = combinedText.Count(char.IsLetter);
        var uppercaseLetters = combinedText.Count(char.IsUpper);
        var punctuationCount = combinedText.Count(char.IsPunctuation);
        var exclamationCount = combinedText.Count(character => character == '!');
        var emotionalCount = words.Count(word => EmotionalWords.Contains(word.ToLowerInvariant()));
        var exaggerationCount = words.Count(word => ExaggerationWords.Contains(word.ToLowerInvariant()));

        return new FeatureSignals
        {
            TextLength = combinedText.Length,
            WordCount = words.Length,
            PunctuationCount = punctuationCount,
            EmotionalWordRatio = words.Length == 0 ? 0 : Math.Round((double)emotionalCount / words.Length, 4),
            UppercaseRatio = totalLetters == 0 ? 0 : Math.Round((double)uppercaseLetters / totalLetters, 4),
            ExclamationCount = exclamationCount,
            ExaggerationCount = exaggerationCount,
            HasSource = !string.IsNullOrWhiteSpace(source)
        };
    }
}
