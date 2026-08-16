<?php

declare(strict_types=1);

namespace ShariaAi\Http;

use ShariaAi\Exceptions\NetworkException;

/**
 * Implementare implicită a transportului HTTP, folosind extensia cURL
 * din PHP (fără dependențe externe suplimentare precum Guzzle).
 */
final class CurlTransport implements HttpTransportInterface
{
    public function __construct(
        private readonly float $connectTimeoutSeconds = 5.0,
        private readonly float $timeoutSeconds = 30.0,
    ) {
    }

    public function request(string $method, string $url, array $headers, ?string $body): HttpResponse
    {
        $ch = curl_init();
        if ($ch === false) {
            throw new NetworkException('Nu s-a putut inițializa cURL.');
        }

        $headerLines = [];
        foreach ($headers as $name => $value) {
            $headerLines[] = "{$name}: {$value}";
        }

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_CUSTOMREQUEST => strtoupper($method),
            CURLOPT_HTTPHEADER => $headerLines,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HEADER => true,
            CURLOPT_CONNECTTIMEOUT_MS => (int) ($this->connectTimeoutSeconds * 1000),
            CURLOPT_TIMEOUT_MS => (int) ($this->timeoutSeconds * 1000),
        ]);

        if ($body !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        }

        $raw = curl_exec($ch);

        if ($raw === false) {
            $error = curl_error($ch);
            $errno = curl_errno($ch);
            curl_close($ch);
            throw new NetworkException("Eroare de rețea la apelarea Sharia-AI API ({$errno}): {$error}");
        }

        $statusCode = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $headerSize = (int) curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        curl_close($ch);

        $rawHeaders = substr($raw, 0, $headerSize);
        $responseBody = substr($raw, $headerSize);

        return new HttpResponse($statusCode, self::parseHeaders($rawHeaders), $responseBody);
    }

    /**
     * @return array<string,string> Chei normalizate la litere mici (headerele HTTP nu sunt case-sensitive).
     */
    private static function parseHeaders(string $rawHeaders): array
    {
        $headers = [];
        foreach (explode("\r\n", trim($rawHeaders)) as $line) {
            if (!str_contains($line, ':')) {
                continue;
            }
            [$name, $value] = explode(':', $line, 2);
            $headers[strtolower(trim($name))] = trim($value);
        }

        return $headers;
    }
}
