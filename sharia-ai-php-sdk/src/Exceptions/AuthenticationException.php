<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Aruncată la un răspuns HTTP 401 — cheia API lipsește sau este
 * invalidă. Verificați parametrul `apiKey` transmis la
 * {@see \ShariaAi\Client::__construct()}.
 */
class AuthenticationException extends ApiException
{
}
