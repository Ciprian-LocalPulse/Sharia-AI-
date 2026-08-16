# Sharia-AI — PHP SDK

[![Tests](https://img.shields.io/badge/tests-27%20passing-brightgreen.svg)](#)

Client PHP oficial pentru API-ul REST [Sharia-AI](https://github.com/Ciprian-LocalPulse/sharia-fintech-ai) — o unealtă open-source pentru screening de conformitate financiară islamică (fond de acțiuni, detecție riba/gharar/maysir în contracte arabe, calcul zakat).

Acest SDK **nu reimplementează** logica de screening/zakat/NLP — este un wrapper subțire peste API-ul REST, responsabil doar de autentificare, serializare JSON, și maparea erorilor HTTP la excepții PHP tipate. Logica de business rămâne o singură sursă de adevăr, în serviciul Python.

## Cerințe

- PHP ≥ 8.1
- Extensiile `curl` și `json` (incluse implicit în majoritatea distribuțiilor PHP)

## Instalare

```bash
composer require sharia-ai/php-sdk
```

## Utilizare rapidă

```php
use ShariaAi\Client;

$client = new Client(apiKey: getenv('SHARIA_AI_API_KEY'), baseUri: 'https://api.exemplu.com');

$result = $client->screenEquity([
    'name' => 'Al-Noor Retail Group',
    'sector' => 'retail',
    'market_cap' => 50_000_000,
    'interest_bearing_debt' => 12_000_000,
    'cash_and_interest_bearing_deposits' => 8_000_000,
    'accounts_receivable' => 15_000_000,
    'total_revenue' => 40_000_000,
    'haram_revenue' => 500_000,
]);

var_dump($result['is_compliant']);
```

## Toate metodele disponibile

```php
$client->health();                                  // GET  /health          — fără autentificare
$client->screenEquity(array $company);               // POST /v1/screening/equity
$client->screenContract(string $text);                // POST /v1/screening/contract
$client->calculateZakat(array $assets);                // POST /v1/zakat/calculate
$client->complianceReport(array $company, ?array $contracts = null, ?array $zakatAssets = null); // POST /v1/compliance/report
$client->auditRecent(int $limit = 50, ?string $eventType = null); // GET /v1/audit/recent — necesită autentificare
```

Fiecare metodă întoarce direct corpul JSON decodat al răspunsului, ca array asociativ PHP — la fel cum este documentat în [`docs/api_reference.md`](https://github.com/Ciprian-LocalPulse/sharia-fintech-ai/blob/main/docs/api_reference.md) al proiectului principal.

## Gestionarea erorilor

SDK-ul mapează codurile HTTP de eroare la excepții PHP tipate, toate derivând din `ShariaAi\Exceptions\ShariaAiException`:

| Cod HTTP | Excepție | Când apare |
|---|---|---|
| — (fără răspuns) | `NetworkException` | Conexiune eșuată, timeout, DNS |
| 401 | `AuthenticationException` | Cheie API lipsă sau invalidă |
| 422 | `ValidationException` | Date de intrare invalide (validare Pydantic pe server) |
| 429 | `RateLimitException` | Limită de cereri depășită; expune `retryAfterSeconds` |
| alt cod ≥ 400 | `ApiException` | Orice altă eroare de server |

```php
use ShariaAi\Exceptions\RateLimitException;
use ShariaAi\Exceptions\ValidationException;
use ShariaAi\Exceptions\AuthenticationException;

try {
    $client->screenEquity($company);
} catch (AuthenticationException $e) {
    // cheia API e greșită sau lipsește
} catch (ValidationException $e) {
    // $e->responseBody conține detaliile complete de validare
} catch (RateLimitException $e) {
    // $e->retryAfterSeconds indică după câte secunde poți reîncerca
    sleep($e->retryAfterSeconds ?? 5);
}
```

## Transport HTTP personalizat / testare

Clientul acceptă un transport HTTP injectabil (implementând `ShariaAi\Http\HttpTransportInterface`), util pentru:
- teste unitare fără apeluri de rețea reale (vezi `tests/FakeTransport.php`)
- înlocuirea cURL cu un alt client HTTP (Guzzle, Symfony HttpClient etc.)

```php
$client = new Client(apiKey: 'test-key', transport: new MockTransportPersonalizat());
```

## Dezvoltare locală

```bash
composer install
composer test              # rulează suita PHPUnit
composer test:coverage     # cu raport de acoperire (necesită xdebug sau pcov)
```

Suita de teste include atât teste unitare (transport fals, fără rețea) cât și teste de **integrare reală** pentru `CurlTransport`, care pornesc un server PHP local (`php -S`) și verifică efectiv cererile/răspunsurile HTTP.

## Licență

MIT — la fel ca proiectul principal Sharia-AI.

## Disclaimer

Această bibliotecă, la fel ca API-ul pe care îl consumă, ajută la fracția tehnică de fond și audit. Nu emite fatwa și nu înlocuiește avizul unui organism de supraveghere Shariah acreditat.
