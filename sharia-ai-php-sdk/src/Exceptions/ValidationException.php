<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Aruncată la un răspuns HTTP 422 — datele trimise nu au trecut
 * validarea Pydantic pe server (câmp lipsă, valoare negativă unde nu
 * e permisă, text de contract prea lung etc.). `$responseBody`
 * conține detaliile structurate ale erorii, așa cum le-a întors API-ul.
 */
class ValidationException extends ApiException
{
}
