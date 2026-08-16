<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Aruncată când cererea HTTP eșuează la nivel de transport
 * (conexiune refuzată, timeout, DNS etc.) — înainte ca serverul să
 * fi apucat să răspundă cu un cod de status.
 */
class NetworkException extends ShariaAiException
{
}
