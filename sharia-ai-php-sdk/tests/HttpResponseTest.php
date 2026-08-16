<?php

declare(strict_types=1);

namespace ShariaAi\Tests;

use PHPUnit\Framework\TestCase;
use ShariaAi\Http\HttpResponse;

final class HttpResponseTest extends TestCase
{
    public function testJsonDecodesValidObjectBody(): void
    {
        $response = new HttpResponse(200, [], '{"a":1,"b":"text"}');
        $this->assertSame(['a' => 1, 'b' => 'text'], $response->json());
    }

    public function testJsonReturnsEmptyArrayForScalarJsonBody(): void
    {
        // json_decode('"just a string"', true) returnează un string, nu un array —
        // json() trebuie să întoarcă [] în acest caz, nu să arunce o eroare de tip.
        $response = new HttpResponse(200, [], '"just a string"');
        $this->assertSame([], $response->json());
    }

    public function testPropertiesAreReadable(): void
    {
        $response = new HttpResponse(404, ['content-type' => 'application/json'], '{}');
        $this->assertSame(404, $response->statusCode);
        $this->assertSame(['content-type' => 'application/json'], $response->headers);
        $this->assertSame('{}', $response->body);
    }
}
