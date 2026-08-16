<?php

declare(strict_types=1);

namespace ShariaAi\Exceptions;

/**
 * Excepția de bază din care derivă toate excepțiile specifice
 * SDK-ului Sharia-AI. Prinderea acesteia acoperă orice eroare
 * provenită din bibliotecă.
 */
class ShariaAiException extends \RuntimeException
{
}
