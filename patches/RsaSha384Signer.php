<?php

/**
 * RsaSha384Signer handles the JWT signature verification for SMART Bulk FHIR OpenID-Connect
 * validation.  Signing algorithm was modified from the jumbojett/OpenID-Connect-PHP project and is licensed under the original
 * Apache2 license of the originating code.
 * @see https://github.com/jumbojett/OpenID-Connect-PHP
 *
 * @package openemr
 * @link      http://www.open-emr.org
 * @author  Michael Jett <mjett@mitre.org>
 * @author    Stephen Nielson <stephen@nielson.org>
 * @copyright  MITRE 2020
 * @copyright Copyright (c) 2021 Stephen Nielson <stephen@nielson.org>
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

namespace OpenEMR\Common\Auth\OpenIDConnect\JWT;

use InvalidArgumentException;
use Lcobucci\JWT\Signer;
use Lcobucci\JWT\Signer\Key;
use OpenEMR\Common\Logging\SystemLogger;
use phpseclib3\Crypt\PublicKeyLoader;
use phpseclib3\Crypt\RSA;
use Psr\Log\LoggerInterface;

class RsaSha384Signer implements Signer
{
    const ALGORITHM_ID = 'RS384';

    const CRYPT_ALGORITHM = 'sha384';

    private $headers;

    /**
     * @var LoggerInterface
     */
    private $logger;

    public function __construct()
    {
        $this->logger = new SystemLogger();
        $this->headers = [];
    }

    /**
     * Returns the algorithm id
     *
     * @return string
     */
    public function algorithmId(): string
    {
        return self::ALGORITHM_ID;
    }

    /**
     * Apply changes on headers according with algorithm
     *
     * @param array $headers
     */
    public function modifyHeader(array &$headers)
    {
        $headers['alg'] = $this->algorithmId();
        $this->headers = $headers;
    }

    /**
     * {@inheritdoc}
     */
    public function sign($payload, $key): string
    {
        // we only handle signature verification not signature creation.
        throw new \BadMethodCallException("This class can only be used for signature verification not signing");
    }

    /**
     * Returns if the expected hash matches with the data and key
     *
     * @param string $expected
     * @param string $payload
     * @param Key|string $key
     *
     * @return boolean
     *
     * @throws InvalidArgumentException When given key is invalid
     */
    public function verify($expected, $payload, $key): bool
    {

        $this->logger->debug("RsaSha384Signer->verify() beginning jwt verification");

        if ($key instanceof JsonWebKeySet) {
            // ZOOMLY PATCH (S7-08 root cause):
            // Upstream reads $this->headers['kid'], but modifyHeader() (which
            // populates that field) is only called during signing, never
            // during verification. The Lcobucci API passes only signature +
            // payload + key to verify() with no token reference, so the
            // upstream code always saw $kid = null. That made
            // JsonWebKeySet::getJSONWebKey() return the FIRST RSA key in the
            // JWKS array regardless of which client's JWT was being verified.
            // Coincidentally works for single-client deployments; for
            // multi-client (multiple registered Zoom accounts sharing one
            // jwks_uri) it caused signature mismatches against any client
            // whose key wasn't first in iteration order.
            //
            // Extract the kid from the base64url-encoded JWT header at the
            // start of $payload instead. $payload is "{header}.{claims}"
            // (the signed portion of the JWT).
            $kid = $this->extractKidFromPayload($payload);
            $this->logger->debug("RsaSha384Signer->verify() attempting to retrieve jwk", ['kid' => $kid]);
            $jwk = $key->getJSONWebKey($kid, $this->algorithmId());
        } else {
            $key = $key instanceof Key ? $key->contents() : $key;
            try {
                $jwk = json_decode($key);
            } catch (\Exception) {
                throw new JWKValidatorException("failed to decode contents of JWKS from key");
            }
        }

        if (
            empty($jwk)
            || !(property_exists($jwk, 'n') && property_exists($jwk, 'e'))
        ) {
            throw new JWKValidatorException('Malformed key object');
        }

        /* We already have base64url-encoded data, so re-encode it as
           regular base64 and use the XML key format for simplicity.
        */
        $public_key_xml = "<RSAKeyValue>\r\n" .
            '  <Modulus>' . $this->b64url2b64($jwk->n) . "</Modulus>\r\n" .
            '  <Exponent>' . $this->b64url2b64($jwk->e) . "</Exponent>\r\n" .
            '</RSAKeyValue>';
        $rsa = PublicKeyLoader::load($public_key_xml)->withPadding(RSA::SIGNATURE_PKCS1)->withHash(self::CRYPT_ALGORITHM);

        return $rsa->verify($payload, $expected);
    }

    /**
     * ZOOMLY PATCH: extract the `kid` JOSE header from a JWT payload string.
     *
     * Lcobucci's Signer::verify() receives $payload as the signed portion of
     * the JWT — "{base64url(header)}.{base64url(claims)}" — with no access
     * to the parsed token. This helper splits, base64url-decodes the header
     * segment, JSON-decodes it, and returns the kid value (or null if the
     * payload is malformed or the kid claim is absent).
     *
     * @param string $payload Signed portion of the JWT (header.claims)
     * @return string|null kid value, or null if it cannot be extracted
     */
    private function extractKidFromPayload(string $payload): ?string
    {
        $parts = explode('.', $payload);
        if (count($parts) < 2) {
            return null;
        }
        $padding = strlen($parts[0]) % 4;
        $header_b64 = $parts[0] . ($padding > 0 ? str_repeat('=', 4 - $padding) : '');
        $header_json = base64_decode(strtr($header_b64, '-_', '+/'), true);
        if ($header_json === false) {
            return null;
        }
        $header = json_decode($header_json, true);
        if (!is_array($header) || !isset($header['kid']) || !is_string($header['kid'])) {
            return null;
        }
        return $header['kid'];
    }

    /**
     * Per RFC4648, "base64 encoding with URL-safe and filename-safe
     * alphabet".  This just replaces characters 62 and 63.  None of the
     * reference implementations seem to restore the padding if necessary,
     * but we'll do it anyway.
     * @param string $base64url
     * @return string
     */
    private function b64url2b64($base64url)
    {
        // "Shouldn't" be necessary, but why not
        $padding = strlen($base64url) % 4;
        if ($padding > 0) {
            $base64url .= str_repeat('=', 4 - $padding);
        }
        return strtr($base64url, '-_', '+/');
    }
}
