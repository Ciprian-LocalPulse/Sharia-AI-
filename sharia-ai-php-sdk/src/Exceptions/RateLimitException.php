<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Aruncată la un răspuns HTTP 429 — s-a depășit limita de cereri
 * configurată pe server pentru acest client (cheie API / IP).
 * `$retryAfterSeconds` provine din antetul `Retry-After` al
 * răspunsului, dacă a fost prezent.
 */
class RateLimitException extends ApiException
{
    /**
     * @param array<string,mixed> $responseBody
     */
    public function __construct(
        string $message,
        int $statusCode,
        array $responseBody,
        public readonly ?int $retryAfterSeconds,
    ) {
        parent::__construct($message, $statusCode, $responseBody);
    }
}
