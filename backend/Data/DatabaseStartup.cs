using System.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

namespace MisinformationRiskAssessment.Api.Data;

public static class DatabaseStartup
{
    private const string AnalysisResultsTableName = "[dbo].[AnalysisResults]";

    public static async Task InitializeAsync(AppDbContext dbContext, ILogger logger, CancellationToken cancellationToken = default)
    {
        await dbContext.Database.MigrateAsync(cancellationToken);

        if (!dbContext.Database.IsRelational())
        {
            return;
        }

        if (await AnalysisResultsTableExistsAsync(dbContext, cancellationToken))
        {
            return;
        }

        logger.LogWarning(
            "Database migration history is present but {TableName} is missing. Repairing the table schema at startup.",
            AnalysisResultsTableName);

        await CreateAnalysisResultsTableAsync(dbContext, cancellationToken);
        logger.LogInformation("Created missing {TableName} table during startup repair.", AnalysisResultsTableName);
    }

    public static async Task<bool> AnalysisResultsTableExistsAsync(AppDbContext dbContext, CancellationToken cancellationToken = default)
    {
        if (!dbContext.Database.IsRelational())
        {
            return true;
        }

        var connection = dbContext.Database.GetDbConnection();
        var shouldClose = connection.State != ConnectionState.Open;

        if (shouldClose)
        {
            await connection.OpenAsync(cancellationToken);
        }

        try
        {
            await using var command = connection.CreateCommand();
            command.CommandText = "SELECT CASE WHEN OBJECT_ID(N'[dbo].[AnalysisResults]', N'U') IS NOT NULL THEN 1 ELSE 0 END;";

            var scalar = await command.ExecuteScalarAsync(cancellationToken);
            return scalar is 1 or 1L or true;
        }
        finally
        {
            if (shouldClose)
            {
                await connection.CloseAsync();
            }
        }
    }

    private static async Task CreateAnalysisResultsTableAsync(AppDbContext dbContext, CancellationToken cancellationToken)
    {
        var sql = """
                  IF OBJECT_ID(N'[dbo].[AnalysisResults]', N'U') IS NULL
                  BEGIN
                      CREATE TABLE [dbo].[AnalysisResults] (
                          [Id] uniqueidentifier NOT NULL,
                          [Title] nvarchar(512) NOT NULL,
                          [Content] nvarchar(max) NULL,
                          [Source] nvarchar(256) NULL,
                          [RiskLevel] nvarchar(32) NOT NULL,
                          [ConfidenceScore] float NOT NULL,
                          [Explanation] nvarchar(2000) NOT NULL,
                          [FeatureSignalsJson] nvarchar(max) NULL,
                          [CreatedAt] datetime2 NOT NULL,
                          CONSTRAINT [PK_AnalysisResults] PRIMARY KEY ([Id])
                      );
                  END
                  """;

        var strategy = dbContext.Database.CreateExecutionStrategy();
        await strategy.ExecuteAsync(async () =>
        {
            await using var transaction = await dbContext.Database.BeginTransactionAsync(cancellationToken);
            await dbContext.Database.ExecuteSqlRawAsync(sql, cancellationToken);
            await transaction.CommitAsync(cancellationToken);
        });
    }
}
