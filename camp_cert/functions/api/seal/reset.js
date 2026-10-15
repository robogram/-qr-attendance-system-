/**
 * Cloudflare Pages Function - /api/seal/reset
 * 기본 직인 복원 API
 */
export async function onRequestPost(context) {
    const { env } = context;

    if (env.CAMP_KV) {
        try {
            await env.CAMP_KV.delete('seal_image_base64');
            const now = Date.now();
            await env.CAMP_KV.put('seal_updated_at', now.toString());
        } catch (e) {
            console.error('KV Delete Error:', e);
        }
    }

    return new Response(JSON.stringify({
        status: 'ok',
        message: '기본 직인으로 초기화되었습니다.'
    }), {
        headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        }
    });
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
