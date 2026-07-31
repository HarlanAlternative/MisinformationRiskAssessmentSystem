namespace MisinformationRiskAssessment.Api.Services;

public sealed class MachineLearningOptions
{
    public string PythonExecutable { get; set; } = "python3";
    public string ClassicalPredictScriptPath { get; set; } = "Services/Ml/classical_predict.py";
    public string ClassicalModelDirectory { get; set; } = "Services/Ml/artifacts";
    public double MediumRiskThreshold { get; set; } = 0.35;
    public double HighRiskThreshold { get; set; } = 0.7;
    public HybridWeightOptions HybridWeights { get; set; } = new();
}

/// <summary>
/// Ensemble weights applied to the component model scores. Tuned on the LIAR
/// validation split by scripts/tune_hybrid_weights.py. This configuration is the
/// single source of truth: scripts/evaluate_hybrid.py reads the same values, so a
/// benchmark can never report weights that this service is not using.
/// </summary>
public sealed class HybridWeightOptions
{
    public double LogisticRegression { get; set; } = 0.5;
    public double RandomForest { get; set; } = 0.3;
    public double Bert { get; set; } = 0.2;
}
