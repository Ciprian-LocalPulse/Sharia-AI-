<?php

/**
 * example.php — demonstrație end-to-end a SDK-ului PHP Sharia-AI,
 * echivalent funcțional cu `examples/demo_screening.py` din
 * proiectul principal.
 *
 * Rulare:
 *   SHARIA_AI_API_KEY=cheia-ta php examples/example.php
 */

declare(strict_types=1);

require __DIR__ . '/../vendor/autoload.php';

use ShariaAi\Client;
use ShariaAi\Exceptions\ShariaAiException;

$client = new Client(
    apiKey: getenv('SHARIA_AI_API_KEY') ?: null,
    baseUri: getenv('SHARIA_AI_BASE_URI') ?: 'http://localhost:8000',
);

try {
    echo "== Screening acțiuni ==\n";
    $equity = $client->screenEquity([
        'name' => 'Al-Noor Retail Group',
        'sector' => 'retail',
        'market_cap' => 50_000_000,
        'interest_bearing_debt' => 12_000_000,
        'cash_and_interest_bearing_deposits' => 8_000_000,
        'accounts_receivable' => 15_000_000,
        'total_revenue' => 40_000_000,
        'haram_revenue' => 500_000,
    ]);
    printf("Companie: %s | Conform: %s\n\n", $equity['company'], $equity['is_compliant'] ? 'da' : 'nu');

    echo "== Analiză contract (arabă) ==\n";
    $contract = $client->screenContract('يُسدد القرض بفائدة سنوية قدرها خمسة بالمئة.');
    printf("Preocupări găsite: %s\n\n", $contract['has_concerns'] ? implode(', ', $contract['categories_found']) : 'niciuna');

    echo "== Calcul zakat ==\n";
    $zakat = $client->calculateZakat(['cash_and_equivalents' => 15_000]);
    printf("Zakat datorat: %s\n\n", $zakat['zakat_due']);

    echo "== Raport de conformitate agregat ==\n";
    $report = $client->complianceReport(
        company: [
            'name' => 'Al-Noor Retail Group',
            'sector' => 'retail',
            'market_cap' => 50_000_000,
            'interest_bearing_debt' => 12_000_000,
            'cash_and_interest_bearing_deposits' => 8_000_000,
            'accounts_receivable' => 15_000_000,
            'total_revenue' => 40_000_000,
            'haram_revenue' => 500_000,
        ],
        zakatAssets: ['cash_and_equivalents' => 15_000],
    );
    printf("Status general: %s\n", $report['overall_status']);
} catch (ShariaAiException $e) {
    fwrite(STDERR, "Eroare Sharia-AI: " . $e->getMessage() . "\n");
    exit(1);
}
