<?php

declare(strict_types=1);

namespace ShariaAi;

use ShariaAi\Exceptions\ApiException;
use ShariaAi\Exceptions\AuthenticationException;
use ShariaAi\Exceptions\RateLimitException;
use ShariaAi\Exceptions\ValidationException;
use ShariaAi\Http\CurlTransport;
use ShariaAi\Http\HttpResponse;
use ShariaAi\Http\HttpTransportInterface;

/**
 * Client PHP pentru API-ul REST Sharia-AI.
 *
 * Acest SDK NU reimplementează logica de screening/zakat/NLP — este un
 * wrapper subțire peste API-ul REST, responsabil doar de: construirea
 * cererilor HTTP, autentificare, (de)serializare JSON, și maparea
 * codurilor de eroare HTTP la excepții PHP tipate.
 *
 * Exemplu de utilizare rapidă:
 * ```php
 * $client = new Client(apiKey: 'cheia-ta-secreta');
 *
 * $result = $client->screenEquity([
 *     'name' => 'Al-Noor Retail Group',
 *     'sector' => 'retail',
 *     'market_cap' => 50_000_000,
 *     'interest_bearing_debt' => 12_000_000,
 *     'cash_and_interest_bearing_deposits' => 8_000_000,
 *     'accounts_receivable' => 15_000_000,
 *     'total_revenue' => 40_000_000,
 *     'haram_revenue' => 500_000,
 * ]);
 *
 * var_dump($result['is_compliant']);
 * ```
 */
final class Client
{
    private const DEFAULT_BASE_URI = 'http://localhost:8000';

    private readonly HttpTransportInterface $transport;
    private readonly string $baseUri;

    public function __construct(
        private readonly ?string $apiKey = null,
        string $baseUri = self::DEFAULT_BASE_URI,
        ?HttpTransportInterface $transport = null,
    ) {
        $this->baseUri = rtrim($baseUri, '/');
        $this->transport = $transport ?? new CurlTransport();
    }

    // ---------- Endpoint-uri publice ----------

    /**
     * Verifică starea de sănătate a serviciului (fără autentificare).
     *
     * @return array<string,mixed>
     */
    public function health(): array
    {
        return $this->request('GET', '/health', requiresAuth: false)->json();
    }

    /**
     * Rulează fluxul de screening al unei companii (POST /v1/screening/equity).
     *
     * @param array<string,mixed> $company
     *
     * @return array<string,mixed>
     */
    public function screenEquity(array $company): array
    {
        return $this->request('POST', '/v1/screening/equity', body: $company)->json();
    }

    /**
     * Analizează un text contractual arab pentru riba/gharar/maysir
     * (POST /v1/screening/contract).
     *
     * @return array<string,mixed>
     */
    public function screenContract(string $text): array
    {
        return $this->request('POST', '/v1/screening/contract', body: ['text' => $text])->json();
    }

    /**
     * Calculează zakat-ul datorat pe baza activelor furnizate
     * (POST /v1/zakat/calculate).
     *
     * @param array<string,mixed> $assets
     *
     * @return array<string,mixed>
     */
    public function calculateZakat(array $assets): array
    {
        return $this->request('POST', '/v1/zakat/calculate', body: $assets)->json();
    }

    /**
     * Generează un raport de conformitate agregat (screening + contracte
     * opționale + zakat opțional), POST /v1/compliance/report.
     *
     * @param array<string,mixed>      $company
     * @param array<string,string>|null $contracts
     * @param array<string,mixed>|null  $zakatAssets
     *
     * @return array<string,mixed>
     */
    public function complianceReport(array $company, ?array $contracts = null, ?array $zakatAssets = null): array
    {
        $payload = ['company' => $company];
        if ($contracts !== null) {
            $payload['contracts'] = $contracts;
        }
        if ($zakatAssets !== null) {
            $payload['zakat_assets'] = $zakatAssets;
        }

        return $this->request('POST', '/v1/compliance/report', body: $payload)->json();
    }

    /**
     * Preia cele mai recente intrări din sistemul de audit (GET /v1/audit/recent).
     * Necesită autentificare întotdeauna.
     *
     * @return array<string,mixed>
     */
    public function auditRecent(int $limit = 50, ?string $eventType = null): array
    {
        $query = ['limit' => (string) $limit];
        if ($eventType !== null) {
            $query['event_type'] = $eventType;
        }

        $queryString = http_build_query($query);

        return $this->request('GET', "/v1/audit/recent?{$queryString}")->json();
    }

    // ---------- Motor intern de cereri ----------

    /**
     * @param array<string,mixed>|null $body
     */
    private function request(
        string $method,
        string $path,
        ?array $body = null,
        bool $requiresAuth = true,
    ): HttpResponse {
        $headers = ['Accept' => 'application/json'];

        if ($requiresAuth && $this->apiKey !== null) {
            $headers['X-API-Key'] = $this->apiKey;
        }

        $encodedBody = null;
        if ($body !== null) {
            $headers['Content-Type'] = 'application/json';
            $encodedBody = json_encode($body, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
        }

        $response = $this->transport->request($method, $this->baseUri . $path, $headers, $encodedBody);

        $this->throwForErrorStatus($response);

        return $response;
    }

    private function throwForErrorStatus(HttpResponse $response): void
    {
        if ($response->statusCode < 400) {
            return;
        }

        $body = $response->json();
        $detail = is_string($body['detail'] ?? null) ? $body['detail'] : 'A apărut o eroare la apelarea Sharia-AI API.';

        match ($response->statusCode) {
            401 => throw new AuthenticationException($detail, $response->statusCode, $body),
            422 => throw new ValidationException($detail, $response->statusCode, $body),
            429 => throw new RateLimitException(
                $detail,
                $response->statusCode,
                $body,
                isset($response->headers['retry-after']) ? (int) $response->headers['retry-after'] : null,
            ),
            default => throw new ApiException($detail, $response->statusCode, $body),
        };
    }
}
