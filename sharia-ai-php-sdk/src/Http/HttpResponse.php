<?php

declare(strict_types=1);

namespace ShariaAi\Http;

/**
 * Reprezintă un răspuns HTTP brut: cod de status, antete, și corp.
 */
final class HttpResponse
{
    /**
     * @param array<string,string> $headers
     */
    public function __construct(
        public readonly int $statusCode,
        public readonly array $headers,
        public readonly string $body,
    ) {
    }

    /**
     * Decodează corpul răspunsului ca JSON asociativ.
     *
     * @return array<string,mixed>
     */
    public function json(): array
    {
        if ($this->body === '') {
            return [];
        }

        $decoded = json_decode($this->body, true);

        return is_array($decoded) ? $decoded : [];
    }
}
