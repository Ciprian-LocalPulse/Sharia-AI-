<?php

declare(strict_types=1);

namespace ShariaAi\Tests;

use PHPUnit\Framework\TestCase;
use ShariaAi\Client;
use ShariaAi\Exceptions\ApiException;
use ShariaAi\Exceptions\AuthenticationException;
use ShariaAi\Exceptions\RateLimitException;
use ShariaAi\Exceptions\ValidationException;
use ShariaAi\Http\HttpResponse;

final class ClientTest extends TestCase
{
    private FakeTransport $transport;
    private Client $client;

    protected function setUp(): void
    {
        $this->transport = new FakeTransport();
        $this->client = new Client(
            apiKey: 'test-api-key',
            baseUri: 'https://sharia-ai.example.com',
            transport: $this->transport,
        );
    }

    private static function jsonResponse(int $status, array $body, array $headers = []): HttpResponse
    {
        return new HttpResponse($status, $headers, json_encode($body, JSON_UNESCAPED_UNICODE));
    }

    // ---------- health() ----------

    public function testHealthDoesNotSendApiKeyHeader(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['status' => 'ok']));

        $result = $this->client->health();

        $this->assertSame(['status' => 'ok'], $result);
        $lastRequest = $this->transport->lastRequest();
        $this->assertSame('GET', $lastRequest['method']);
        $this->assertSame('https://sharia-ai.example.com/health', $lastRequest['url']);
        $this->assertArrayNotHasKey('X-API-Key', $lastRequest['headers']);
    }

    // ---------- screenEquity() ----------

    public function testScreenEquitySendsCorrectRequestAndParsesResponse(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, [
            'company' => 'Al-Noor',
            'is_compliant' => true,
            'purification_ratio' => 0.0,
            'checks' => [],
        ]));

        $result = $this->client->screenEquity([
            'name' => 'Al-Noor',
            'sector' => 'retail',
            'market_cap' => 1000.0,
            'interest_bearing_debt' => 0.0,
            'cash_and_interest_bearing_deposits' => 0.0,
            'accounts_receivable' => 0.0,
            'total_revenue' => 500.0,
            'haram_revenue' => 0.0,
        ]);

        $this->assertTrue($result['is_compliant']);

        $lastRequest = $this->transport->lastRequest();
        $this->assertSame('POST', $lastRequest['method']);
        $this->assertSame('https://sharia-ai.example.com/v1/screening/equity', $lastRequest['url']);
        $this->assertSame('test-api-key', $lastRequest['headers']['X-API-Key']);
        $this->assertSame('application/json', $lastRequest['headers']['Content-Type']);

        $decodedBody = json_decode($lastRequest['body'], true);
        $this->assertSame('Al-Noor', $decodedBody['name']);
    }

    public function testScreenEquitySerializesArabicTextWithoutEscaping(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['is_compliant' => true]));

        $this->client->screenEquity(['name' => 'شركة الاختبار', 'sector' => 'other']);

        $lastRequest = $this->transport->lastRequest();
        $this->assertStringContainsString('شركة الاختبار', $lastRequest['body']);
    }

    // ---------- screenContract() ----------

    public function testScreenContractSendsTextAsBody(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, [
            'has_concerns' => true,
            'categories_found' => ['riba'],
            'flags' => [],
        ]));

        $result = $this->client->screenContract('هذا القرض بفائدة');

        $this->assertTrue($result['has_concerns']);
        $lastRequest = $this->transport->lastRequest();
        $decodedBody = json_decode($lastRequest['body'], true);
        $this->assertSame('هذا القرض بفائدة', $decodedBody['text']);
    }

    // ---------- calculateZakat() ----------

    public function testCalculateZakatReturnsDecodedResult(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, [
            'meets_nisab' => true,
            'zakat_due' => 250.0,
        ]));

        $result = $this->client->calculateZakat(['cash_and_equivalents' => 10000.0]);

        $this->assertTrue($result['meets_nisab']);
        $this->assertEquals(250.0, $result['zakat_due']);
    }

    // ---------- complianceReport() ----------

    public function testComplianceReportOmitsOptionalFieldsWhenNull(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['overall_status' => 'ok']));

        $this->client->complianceReport(['name' => 'X']);

        $lastRequest = $this->transport->lastRequest();
        $decodedBody = json_decode($lastRequest['body'], true);
        $this->assertArrayHasKey('company', $decodedBody);
        $this->assertArrayNotHasKey('contracts', $decodedBody);
        $this->assertArrayNotHasKey('zakat_assets', $decodedBody);
    }

    public function testComplianceReportIncludesOptionalFieldsWhenProvided(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['overall_status' => 'ok']));

        $this->client->complianceReport(
            company: ['name' => 'X'],
            contracts: ['c1' => 'نص العقد'],
            zakatAssets: ['cash_and_equivalents' => 100.0],
        );

        $lastRequest = $this->transport->lastRequest();
        $decodedBody = json_decode($lastRequest['body'], true);
        $this->assertSame(['c1' => 'نص العقد'], $decodedBody['contracts']);
        $this->assertEquals(100.0, $decodedBody['zakat_assets']['cash_and_equivalents']);
    }

    // ---------- auditRecent() ----------

    public function testAuditRecentBuildsQueryString(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['total_entries' => 0, 'entries' => []]));

        $this->client->auditRecent(limit: 10, eventType: 'zakat_calculation');

        $lastRequest = $this->transport->lastRequest();
        $this->assertSame('GET', $lastRequest['method']);
        $this->assertStringContainsString('limit=10', $lastRequest['url']);
        $this->assertStringContainsString('event_type=zakat_calculation', $lastRequest['url']);
    }

    public function testAuditRecentSendsApiKey(): void
    {
        $this->transport->queueResponse(self::jsonResponse(200, ['total_entries' => 0, 'entries' => []]));

        $this->client->auditRecent();

        $lastRequest = $this->transport->lastRequest();
        $this->assertSame('test-api-key', $lastRequest['headers']['X-API-Key']);
    }

    // ---------- Mapare erori -> excepții ----------

    public function testMissingOrInvalidApiKeyThrowsAuthenticationException(): void
    {
        $this->transport->queueResponse(self::jsonResponse(401, ['detail' => 'مفتاح API مفقود أو غير صالح.']));

        $this->expectException(AuthenticationException::class);
        $this->expectExceptionMessage('مفتاح API مفقود أو غير صالح.');

        $this->client->screenEquity(['name' => 'X']);
    }

    public function testValidationErrorThrowsValidationException(): void
    {
        $this->transport->queueResponse(self::jsonResponse(422, ['detail' => 'market_cap يجب أن يكون أكبر من صفر']));

        try {
            $this->client->screenEquity(['name' => 'X', 'market_cap' => 0]);
            $this->fail('Trebuia să arunce ValidationException.');
        } catch (ValidationException $exception) {
            $this->assertSame(422, $exception->statusCode);
            $this->assertSame('market_cap يجب أن يكون أكبر من صفر', $exception->getMessage());
        }
    }

    public function testRateLimitExceededThrowsRateLimitExceptionWithRetryAfter(): void
    {
        $this->transport->queueResponse(self::jsonResponse(
            429,
            ['detail' => 'تم تجاوز حد معدّل الطلبات'],
            ['retry-after' => '60'],
        ));

        try {
            $this->client->calculateZakat(['cash_and_equivalents' => 1.0]);
            $this->fail('Trebuia să arunce RateLimitException.');
        } catch (RateLimitException $exception) {
            $this->assertSame(429, $exception->statusCode);
            $this->assertSame(60, $exception->retryAfterSeconds);
        }
    }

    public function testRateLimitExceptionRetryAfterIsNullWhenHeaderMissing(): void
    {
        $this->transport->queueResponse(self::jsonResponse(429, ['detail' => 'too many']));

        try {
            $this->client->calculateZakat(['cash_and_equivalents' => 1.0]);
            $this->fail('Trebuia să arunce RateLimitException.');
        } catch (RateLimitException $exception) {
            $this->assertNull($exception->retryAfterSeconds);
        }
    }

    public function testServerErrorThrowsGenericApiException(): void
    {
        $this->transport->queueResponse(self::jsonResponse(500, ['detail' => 'خطأ داخلي غير متوقّع']));

        try {
            $this->client->screenEquity(['name' => 'X']);
            $this->fail('Trebuia să arunce ApiException.');
        } catch (ApiException $exception) {
            $this->assertSame(500, $exception->statusCode);
            $this->assertNotInstanceOf(ValidationException::class, $exception);
            $this->assertNotInstanceOf(AuthenticationException::class, $exception);
            $this->assertNotInstanceOf(RateLimitException::class, $exception);
        }
    }

    public function testApiExceptionExposesStatusCodeAndBody(): void
    {
        $this->transport->queueResponse(self::jsonResponse(503, ['detail' => 'service unavailable']));

        try {
            $this->client->auditRecent();
            $this->fail('Trebuia să arunce ApiException.');
        } catch (ApiException $exception) {
            $this->assertSame(503, $exception->statusCode);
            $this->assertSame('service unavailable', $exception->responseBody['detail']);
        }
    }

    public function testErrorResponseWithoutDetailFieldUsesFallbackMessage(): void
    {
        $this->transport->queueResponse(self::jsonResponse(500, []));

        try {
            $this->client->screenEquity(['name' => 'X']);
            $this->fail('Trebuia să arunce ApiException.');
        } catch (ApiException $exception) {
            $this->assertNotEmpty($exception->getMessage());
        }
    }

    // ---------- Client fără cheie API (mod dezvoltare) ----------

    public function testClientWithoutApiKeyDoesNotSendHeader(): void
    {
        $devClient = new Client(baseUri: 'https://sharia-ai.example.com', transport: $this->transport);
        $this->transport->queueResponse(self::jsonResponse(200, ['is_compliant' => true]));

        $devClient->screenEquity(['name' => 'X']);

        $lastRequest = $this->transport->lastRequest();
        $this->assertArrayNotHasKey('X-API-Key', $lastRequest['headers']);
    }

    // ---------- HttpResponse ----------

    public function testHttpResponseJsonReturnsEmptyArrayForEmptyBody(): void
    {
        $response = new HttpResponse(204, [], '');
        $this->assertSame([], $response->json());
    }

    public function testHttpResponseJsonReturnsEmptyArrayForNonJsonBody(): void
    {
        $response = new HttpResponse(200, [], 'not json at all');
        $this->assertSame([], $response->json());
    }
}
