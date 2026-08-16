<?php

declare(strict_types=1);

namespace ShariaAi\Tests;

use ShariaAi\Http\HttpResponse;
use ShariaAi\Http\HttpTransportInterface;

/**
 * Transport HTTP fals, folosit exclusiv în teste. Nu face nicio
 * conexiune de rețea reală; întoarce răspunsuri pre-programate și
 * înregistrează fiecare cerere primită, pentru a putea fi inspectată
 * ulterior în assertions.
 */
final class FakeTransport implements HttpTransportInterface
{
    /** @var HttpResponse[] */
    private array $queuedResponses = [];

    /** @var array<int,array{method:string,url:string,headers:array<string,string>,body:?string}> */
    public array $recordedRequests = [];

    public function queueResponse(HttpResponse $response): void
    {
        $this->queuedResponses[] = $response;
    }

    public function request(string $method, string $url, array $headers, ?string $body): HttpResponse
    {
        $this->recordedRequests[] = [
            'method' => $method,
            'url' => $url,
            'headers' => $headers,
            'body' => $body,
        ];

        if (empty($this->queuedResponses)) {
            throw new \RuntimeException('FakeTransport: nu mai sunt răspunsuri programate în coadă.');
        }

        return array_shift($this->queuedResponses);
    }

    public function lastRequest(): ?array
    {
        return $this->recordedRequests === [] ? null : $this->recordedRequests[count($this->recordedRequests) - 1];
    }
}
