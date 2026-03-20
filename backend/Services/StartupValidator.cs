namespace MisinformationRiskAssessment.Api.Services;

public static class StartupValidator
{
    public static void Validate(IConfiguration configuration, string contentRootPath)
    {
        var machineLearningSection = configuration.GetSection("MachineLearning");
        var bertSection = configuration.GetSection("BertService");

        var pythonExecutable = machineLearningSection["PythonExecutable"] ?? "python3";
        var scriptPath = ResolvePath(contentRootPath, machineLearningSection["ClassicalPredictScriptPath"] ?? "Services/Ml/classical_predict.py");
        var modelDirectory = ResolvePath(contentRootPath, machineLearningSection["ClassicalModelDirectory"] ?? "Services/Ml/artifacts");
        var bertUrl = bertSection["Url"];

        var errors = new List<string>();

        if (!PythonExecutableResolver.TryResolve(pythonExecutable, out _))
        {
            errors.Add(
                $"Python executable '{pythonExecutable}' was not found. " +
                "Set MachineLearning__PythonExecutable to a valid interpreter, or leave it unset to allow automatic detection."
            );
        }

        if (!File.Exists(scriptPath))
        {
            errors.Add($"Classical prediction script was not found at '{scriptPath}'.");
        }

        if (!Directory.Exists(modelDirectory))
        {
            errors.Add($"Classical model artifact directory was not found at '{modelDirectory}'. Run scripts/train_all.sh or train_classical_models.py first.");
        }
        else
        {
            var requiredArtifacts = new[]
            {
                "tfidf_vectorizer.joblib",
                "logistic_regression.joblib",
                "random_forest.joblib"
            };

            foreach (var artifact in requiredArtifacts)
            {
                var artifactPath = Path.Combine(modelDirectory, artifact);
                if (!File.Exists(artifactPath))
                {
                    errors.Add($"Required classical model artifact is missing: '{artifactPath}'. Run scripts/train_all.sh or train_classical_models.py first.");
                }
            }
        }

        if (string.IsNullOrWhiteSpace(bertUrl))
        {
            errors.Add("BertService__Url is missing. Set it to the running FastAPI service address, for example http://localhost:8001.");
        }
        else if (!Uri.TryCreate(bertUrl, UriKind.Absolute, out var parsedUri) ||
                 (parsedUri.Scheme != Uri.UriSchemeHttp && parsedUri.Scheme != Uri.UriSchemeHttps))
        {
            errors.Add($"BertService__Url '{bertUrl}' is invalid. Use an absolute http/https URL, for example http://localhost:8001.");
        }

        if (errors.Count > 0)
        {
            throw new InvalidOperationException("Startup validation failed:" + Environment.NewLine + string.Join(Environment.NewLine, errors.Select(error => $"- {error}")));
        }
    }

    private static string ResolvePath(string contentRootPath, string configuredPath)
    {
        if (Path.IsPathRooted(configuredPath))
        {
            return configuredPath;
        }

        return Path.GetFullPath(Path.Combine(contentRootPath, configuredPath));
    }
}
