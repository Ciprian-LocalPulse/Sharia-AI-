<?php

declare(strict_types=1);

namespace ShariaAi\Tests;

use PHPUnit\Framework\TestCase;
use ShariaAi\Http\CurlTransport;

/**
 * Teste de INTEGRARE pentru {@see CurlTransport}: pornesc un server
 * PHP local real (`php -S`) și fac cereri HTTP efective către el, spre
 * deosebire de {@see ClientTest}, care folosește un transport fals.
 * Acest lucru garantează că implementarea cURL construiește corect
 * metoda, antetele, corpul, și că parsează corect statusul/antetele
 * din răspuns.
 */
final class CurlTransportTest extends TestCase
{
    private static int $port;
    private static $serverProcess;

    public static function setUpBeforeClass(): void
    {
        self::$port = 18000 + random_int(0, 999);
        $router = __DIR__ . '/fixtures/router.php';
        $descriptors = [1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
        self::$serverProcess = proc_open(
            sprintf('php -S 127.0.0.1:%d %s', self::$port, escapeshellarg($router)),
            $descriptors,
            $pipes,
        );

        // Așteaptă până când serverul răspunde efectiv, în loc de un sleep fix.
        $deadline = microtime(true) + 5.0;
        while (microtime(true) < $deadline) {
            $ch = curl_init("http://127.0.0.1:" . self::$port . "/");
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT_MS, 200);
            $result = curl_exec($ch);
            curl_close($ch);
            if ($result !== false) {
                return;
            }
            usleep(50_000);
        }

        self::fail('Serverul PHP local de test nu a pornit la timp.');
    }

    public static function tearDownAfterClass(): void
    {
        if (is_resource(self::$serverProcess)) {
            proc_terminate(self::$serverProcess);
            proc_close(self::$serverProcess);
        }
    }

    private function baseUrl(): string
    {
        return 'http://127.0.0.1:' . self::$port;
    }

    public function testGetRequestReturnsStatusAndBody(): void
    {
        $transport = new CurlTransport();
        $response = $transport->request('GET', $this->baseUrl() . '/', ['Accept' => 'application/json'], null);

        $this->assertSame(200, $response->statusCode);
        $this->assertSame(['status' => 'ok'], $response->json());
    }

    public function testPostRequestSendsBodyAndHeaders(): void
    {
        $transport = new CurlTransport();
        $response = $transport->request(
            'POST',
            $this->baseUrl() . '/echo',
            ['Content-Type' => 'application/json', 'X-API-Key' => 'secret-123'],
            '{"a":1}',
        );

        $decoded = $response->json();
        $this->assertSame('POST', $decoded['method']);
        $this->assertSame('{"a":1}', $decoded['received_body']);
        $this->assertSame('secret-123', $decoded['received_header_x_api_key']);
    }

    public function test404StatusIsReturnedNotThrown(): void
    {
        $transport = new CurlTransport();
        $response = $transport->request('GET', $this->baseUrl() . '/status/404', [], null);

        $this->assertSame(404, $response->statusCode);
        $this->assertSame('not found', $response->json()['detail']);
    }

    public function testResponseHeadersAreParsedCaseInsensitively(): void
    {
        $transport = new CurlTransport();
        $response = $transport->request('GET', $this->baseUrl() . '/status/429', [], null);

        $this->assertSame(429, $response->statusCode);
        $this->assertSame('42', $response->headers['retry-after']);
    }

    public function testUnreachableHostThrowsNetworkException(): void
    {
        $transport = new CurlTransport(connectTimeoutSeconds: 0.5, timeoutSeconds: 0.5);

        $this->expectException(\ShariaAi\Exceptions\NetworkException::class);
        $transport->request('GET', 'http://127.0.0.1:1/unreachable', [], null);
    }
}
