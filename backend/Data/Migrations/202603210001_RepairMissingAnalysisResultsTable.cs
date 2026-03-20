using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace MisinformationRiskAssessment.Api.Data.Migrations
{
    public partial class RepairMissingAnalysisResultsTable : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
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
                """);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                """
                IF OBJECT_ID(N'[dbo].[AnalysisResults]', N'U') IS NOT NULL
                BEGIN
                    DROP TABLE [dbo].[AnalysisResults];
                END
                """);
        }
    }
}
