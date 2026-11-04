<?php
/**
 * Read-only conformance harness for BITS Accessible Forms' BFL parser and
 * formatter. QUILL's forms tests run it, when PHP and a BAF checkout are both
 * on the machine, to compare QUILL's Python port with BAF's own PHP.
 *
 * Usage: php baf_php_harness.php <baf-root> <sources.json>
 *
 * <sources.json> is a JSON list of BFL source strings. The harness prints a
 * JSON list of {"parse": <BAF parse result>, "format": <BAF formatter text>}
 * to stdout. It only `require`s BAF's files; it writes nothing anywhere.
 *
 * WordPress is not loaded, so the few WordPress functions BAF's BFL classes
 * call are stubbed here. `sanitize_title` is the one that matters: it is a
 * port of WordPress's sanitize_title_with_dashes ('save' context) for the
 * inputs BFL produces, and quill/core/forms/baf_compat.py ports this stub
 * exactly, so both sides agree by construction.
 */

define( 'ABSPATH', __DIR__ );

function bafh_remove_accents( $s ) {
    if ( ! preg_match( '/[\x80-\xff]/', $s ) ) {
        return $s;
    }
    if ( class_exists( 'Normalizer' ) ) {
        $n = Normalizer::normalize( $s, Normalizer::FORM_KD );
        if ( $n !== false ) {
            $s = preg_replace( '/\p{Mn}+/u', '', $n );
        }
    }
    return $s;
}

function sanitize_title( $title ) {
    $title = bafh_remove_accents( (string) $title );
    $title = strip_tags( $title );
    $title = preg_replace( '|%([a-fA-F0-9][a-fA-F0-9])|', '---$1---', $title );
    $title = str_replace( '%', '', $title );
    $title = preg_replace( '|---([a-fA-F0-9][a-fA-F0-9])---|', '%$1', $title );
    if ( preg_match( '/[\x80-\xff]/', $title ) ) {
        $title = mb_strtolower( $title, 'UTF-8' );
        $out = '';
        $len = strlen( $title );
        for ( $i = 0; $i < $len; $i++ ) {
            $c = ord( $title[ $i ] );
            $out .= $c < 128 ? $title[ $i ] : '%' . strtolower( sprintf( '%02X', $c ) );
        }
        $title = $out;
    }
    $title = strtolower( $title );
    $title = preg_replace( '/&.+?;/', '', $title );
    $title = str_replace( '.', '-', $title );
    $title = preg_replace( '/[^%a-z0-9 _-]/', '', $title );
    $title = preg_replace( '/\s+/', '-', $title );
    $title = preg_replace( '|-+|', '-', $title );
    return trim( $title, '-' );
}

$root    = rtrim( $argv[1], '/\\' ) . '/';
$sources = json_decode( file_get_contents( $argv[2] ), true );

require_once $root . 'includes/bfl/class-baf-bfl-lexer.php';
require_once $root . 'includes/bfl/class-baf-bfl-parser.php';
require_once $root . 'includes/bfl/class-baf-bfl-formatter.php';

$out = array();
foreach ( $sources as $source ) {
    $parser    = new BAF_BFL_Parser();
    $formatter = new BAF_BFL_Formatter();
    $out[]     = array(
        'parse'  => $parser->parse( $source ),
        'format' => $formatter->format( $source ),
    );
}
echo json_encode( $out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION );
