namespace MisinformationRiskAssessment.Api.Services;

public sealed class MachineLearningOptions
{
    public string PythonExecutable { get; set; } = "python3";
    public string ClassicalPredictScriptPath { get; set; } = "Services/Ml/classical_predict.py";
    public string ClassicalModelDirectory { get; set; } = "Services/Ml/artifacts";
    public double MediumRiskThreshold { get; set; } = 0.35;
    public double HighRiskThreshold { get; set; } = 0.7;
}
