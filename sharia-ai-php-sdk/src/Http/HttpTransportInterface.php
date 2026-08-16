<?php

declare(strict_types=1);

namespace ShariaAi\Http;

/**
 * Abstractizare minimală peste transportul HTTP, pentru a permite
 * injectarea unui transport fals (fake) în teste, fără apeluri de
 * rețea reale. Implementarea implicită este {@see CurlTransport}.
 */
interface HttpTransportInterface
{
    /**
     * Execută o cerere HTTP și întoarce răspunsul brut.
     *
     * @param string               $method  Metoda HTTP (GET, POST, ...)
     * @param string               $url     URL-ul complet al cererii
     * @param array<string,string> $headers Antete cheie => valoare
     * @param string|null          $body    Corpul cererii (JSON deja serializat) sau null
     *
     * @return HttpResponse
     */
    public function request(string $method, string $url, array $headers, ?string $body): HttpResponse;
}
