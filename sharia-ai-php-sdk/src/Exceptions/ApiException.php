<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Aruncată pentru orice răspuns de eroare provenit efectiv de la
 * serverul Sharia-AI (spre deosebire de {@see NetworkException}, care
 * indică absența unui răspuns). Păstrează codul de status HTTP și
 * corpul JSON decodat, pentru diagnosticare completă.
 */
class ApiException extends ShariaAiException
{
    /**
     * @param array<string,mixed> $responseBody
     */
    public function __construct(
        string $message,
        public readonly int $statusCode,
        public readonly array $responseBody = [],
    ) {
        parent::__construct($message);
    }
}
