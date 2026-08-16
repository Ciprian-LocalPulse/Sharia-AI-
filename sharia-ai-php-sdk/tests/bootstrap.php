<?php

declare(strict_types=1);

/**
 * bootstrap.php — autoloader PSR-4 minimalist folosit DOAR pentru
 * rularea locală a testelor în medii fără acces la `composer install`
 * (de exemplu sandbox-uri izolate de rețea). Consumatorii reali ai
 * acestei biblioteci trebuie să folosească `vendor/autoload.php`
 * generat de Composer, ca în orice pachet PHP standard.
 */

spl_autoload_register(static function (string $class): void {
    $prefixes = [
        'ShariaAi\\Tests\\' => __DIR__ . '/',
        'ShariaAi\\' => __DIR__ . '/../src/',
    ];

    foreach ($prefixes as $prefix => $baseDir) {
        if (!str_starts_with($class, $prefix)) {
            continue;
        }
        $relative = substr($class, strlen($prefix));
        $file = $baseDir . str_replace('\\', '/', $relative) . '.php';
        if (is_file($file)) {
            require $file;
            return;
        }
    }
});
