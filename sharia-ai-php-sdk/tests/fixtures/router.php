<?php

declare(strict_types=1);

/**
 * router.php — server minimalist folosit DOAR de {@see CurlTransportTest}
 * pentru a testa transportul cURL real, fără dependențe externe.
 * Se pornește cu: php -S 127.0.0.1:PORT router.php
 */

header('X-Echo-Method: ' . $_SERVER['REQUEST_METHOD']);

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($path === '/echo') {
    $body = file_get_contents('php://input');
    header('Content-Type: application/json');
    echo json_encode([
        'method' => $_SERVER['REQUEST_METHOD'],
        'received_body' => $body,
        'received_header_x_api_key' => $_SERVER['HTTP_X_API_KEY'] ?? null,
    ]);
    exit;
}

if ($path === '/status/404') {
    http_response_code(404);
    header('Content-Type: application/json');
    echo json_encode(['detail' => 'not found']);
    exit;
}

if ($path === '/status/429') {
    http_response_code(429);
    header('Retry-After: 42');
    header('Content-Type: application/json');
    echo json_encode(['detail' => 'rate limited']);
    exit;
}

http_response_code(200);
header('Content-Type: application/json');
echo json_encode(['status' => 'ok']);
