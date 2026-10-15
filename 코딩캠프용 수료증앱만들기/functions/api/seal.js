/**
 * Cloudflare Pages Function - /api/seal
 * 실시간 직인 이미지 서빙 및 업로드 API
 */
export async function onRequestGet(context) {
    const { env, request } = context;

    // 1. Cloudflare KV에 커스텀 직인 이미지가 있으면 서빙
    if (env.CAMP_KV) {
        try {
            const customSealBase64 = await env.CAMP_KV.get('seal_image_base64');
            if (customSealBase64) {
                // Base64 to Uint8Array Binary
                const binaryStr = atob(customSealBase64);
                const bytes = new Uint8Array(binaryStr.length);
                for (let i = 0; i < binaryStr.length; i++) {
                    bytes[i] = binaryStr.charCodeAt(i);
                }
                return new Response(bytes.buffer, {
                    headers: {
                        'Content-Type': 'image/png',
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'no-cache, no-store, must-revalidate'
                    }
                });
            }
        } catch (e) {
            console.error('Seal KV Read Error:', e);
        }
    }

    // 2. 기본 직인 이미지로 302 리다이렉트
    const url = new URL(request.url);
    return Response.redirect(`${url.origin}/assets/seal.png`, 302);
}

export async function onRequestPost(context) {
    const { env, request } = context;

    try {
        const body = await request.json();
        let imgData = body.image || '';
        if (imgData.includes(',')) {
            imgData = imgData.split(',')[1];
        }

        const now = Date.now();

        if (env.CAMP_KV) {
            await env.CAMP_KV.put('seal_image_base64', imgData);
            await env.CAMP_KV.put('seal_updated_at', now.toString());
        }

        return new Response(JSON.stringify({
            status: 'ok',
            seal_url: `/api/seal?t=${now}`,
            updated_at: now
        }), {
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            }
        });
    } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
            status: 400,
            headers: {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            }
        });
    }
}

export async function onRequestOptions() {
    return new Response(null, {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    });
}
