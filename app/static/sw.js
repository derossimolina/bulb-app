/*
 * WYW — service worker do app instalável (PWA), alternativa ao app Android até ele sair.
 *
 * - Páginas: sempre da rede. Sem rede, só a página inicial (sem resultados) vem guardada; uma busca mostra
 *   /offline. Previsão e risco nunca são guardados: dado de risco velho é pior que nenhum (SPEC.md REQ-PWA-01).
 * - Arquivos do site (CSS, JS, ícones, logo): devolve o guardado e atualiza em segundo plano.
 * - Fontes do Google: guardadas depois do primeiro uso.
 * - APIs de tempo, endereço e avisos (Open-Meteo, Nominatim, INMET) nunca são guardadas:
 *   o risco precisa de dado atual (SPEC.md REQ-ALERTA-07).
 * Servido em /sw.js (routes.py) para controlar o site inteiro.
 */
'use strict';

var VERSION = 'wyw-v2';  // mude a cada versão do visual, para o app instalado baixar tudo de novo
var SHELL = VERSION + '-shell';
var PAGES = VERSION + '-pages';
var PRECACHE = [
    '/offline',
    '/static/style.css',
    '/static/risk.js',
    '/static/wyw.js',
    '/static/icons.svg',
    '/static/brand/jeronimo-lockup-principal.svg',
    '/static/brand/jeronimo-lockup-principal-claro.svg',
    '/static/pwa/icon-192.png',
    '/static/pwa/favicon-32.png'
];
var FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', function (event) {
    event.waitUntil(caches.open(SHELL).then(function (cache) { return cache.addAll(PRECACHE); })
        .then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (event) {
    event.waitUntil(caches.keys().then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k.indexOf(VERSION) !== 0; })
            .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); }));
});

function networkFirstPage(request) {
    var home = new URL(request.url).search === '' || /^\?(lang=\w+|source=pwa)$/.test(new URL(request.url).search);
    return fetch(request).then(function (response) {
        // Guarda só a página inicial, que não tem previsão nem risco
        if (response.ok && home) {
            var copy = response.clone();
            caches.open(PAGES).then(function (cache) { return cache.put(request, copy); });
        }
        return response;
    }).catch(function () {
        return (home ? caches.match(request) : Promise.resolve(null))
            .then(function (hit) { return hit || caches.match('/offline'); });
    });
}

function staleWhileRevalidate(request, cacheName) {
    return caches.open(cacheName).then(function (cache) {
        return cache.match(request).then(function (hit) {
            var fresh = fetch(request).then(function (response) {
                if (response.ok || response.type === 'opaque') cache.put(request, response.clone());
                return response;
            }).catch(function () { return hit; });
            return hit || fresh;
        });
    });
}

self.addEventListener('fetch', function (event) {
    var request = event.request;
    if (request.method !== 'GET') return;
    var url = new URL(request.url);

    if (url.origin === self.location.origin) {
        if (request.mode === 'navigate') { event.respondWith(networkFirstPage(request)); return; }
        if (url.pathname.indexOf('/static/') === 0) { event.respondWith(staleWhileRevalidate(request, SHELL)); return; }
        return;  // manifesto, /healthz e demais: sempre da rede
    }
    if (FONT_HOSTS.indexOf(url.hostname) !== -1) event.respondWith(staleWhileRevalidate(request, SHELL));
    // Demais origens (APIs de tempo e avisos, bandeiras): rede, sem guardar
});
