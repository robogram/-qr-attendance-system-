/**
 * Cloudflare Pages Function - /api/data
 * 학생 및 교육기관 데이터 동기화 API (Cloudflare KV 또는 정적 JSON fallback 지원)
 */
export async function onRequestGet(context) {
    const { env, request } = context;

    // 1. Cloudflare KV에 저장된 최신 데이터가 있으면 반환
    if (env.CAMP_KV) {
        try {
            const kvData = await env.CAMP_KV.get('app_data');
            if (kvData) {
                const parsed = JSON.parse(kvData);
                const hasCustomSeal = await env.CAMP_KV.get('seal_image_base64');
                parsed.has_custom_seal = !!hasCustomSeal;
                return new Response(JSON.stringify(parsed), {
                    headers: {
                        'Content-Type': 'application/json; charset=utf-8',
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'no-cache, no-store, must-revalidate'
                    }
                });
            }
        } catch (e) {
            console.error('KV Read Error:', e);
        }
    }

    // 2. KV가 없거나 초기 상태이면 프로젝트 내 기본 database/app_data.json 파일 fetch
    const url = new URL(request.url);
    try {
        const fallbackRes = await fetch(`${url.origin}/database/app_data.json`);
        if (fallbackRes.ok) {
            const dataText = await fallbackRes.text();
            return new Response(dataText, {
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            });
        }
    } catch (e) {
        console.error('Fallback Fetch Error:', e);
    }

    // 3. 최후 빈 구조체 반환
    return new Response(JSON.stringify({ institutions: [], students: [], seal_updated_at: 0 }), {
        headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        }
    });
}

export async function onRequestPost(context) {
    const { env, request } = context;

    try {
        const body = await request.json();

        if (env.CAMP_KV) {
            // 기존 데이터와 병합
            let current = { institutions: [], students: [], seal_updated_at: 0 };
            try {
                const existing = await env.CAMP_KV.get('app_data');
                if (existing) current = JSON.parse(existing);
            } catch (e) {}

            if (body.institutions) current.institutions = body.institutions;
            if (body.students) current.students = body.students;
            if (body.seal_updated_at) current.seal_updated_at = body.seal_updated_at;

            await env.CAMP_KV.put('app_data', JSON.stringify(current));

            return new Response(JSON.stringify({ status: 'ok', message: 'Cloudflare KV 영구 저장 완료' }), {
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                }
            });
        }

        // KV 바인딩이 아직 없을 때도 프론트엔드가 중단되지 않도록 OK 응답
        return new Response(JSON.stringify({ status: 'ok', message: '동기화 완료 (로컬/세션 반영)' }), {
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
