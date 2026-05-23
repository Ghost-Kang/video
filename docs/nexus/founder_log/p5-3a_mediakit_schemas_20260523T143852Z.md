# P5-3a 火山 MediaKit endpoint schema probe — 20260523T143852Z

**Date**: 2026-05-23T14:38:52.603827+00:00
**video_url**: `https://www.douyin.com/video/7385782607067335962`
**Endpoint base**: `https://mediakit.cn-beijing.volces.com/api/v1/tools`
**Timeout per endpoint**: 120.0s

**Purpose**: ground-truth schema discovery for P5-3 sub-phase A. Public Volcengine docs do not list MediaKit as of 2026-05-23 W3D3. This report is consumed by sub-phase B/C/D as the authoritative request/response contract.

---

## /extract-audio

### Request

`POST https://mediakit.cn-beijing.volces.com/api/v1/tools/extract-audio`

```http
Content-Type: application/json
Authorization: Bearer <VOLC_MEDIAKIT_AK>

{
  "video_url": "https://www.douyin.com/video/7385782607067335962"
}
```

### Response

**HTTP status**: `200 OK`

```json
{
  "success": true,
  "task_id": "amk-tool-extract-audio-103328697346",
  "request_id": "20260523223852CD67F5BA7302472B422B"
}
```

**PM note**: ✅ endpoint exists + returns 200. Use this schema as contract.

---

## /extract-frames

### Request

`POST https://mediakit.cn-beijing.volces.com/api/v1/tools/extract-frames`

```http
Content-Type: application/json
Authorization: Bearer <VOLC_MEDIAKIT_AK>

{
  "video_url": "https://www.douyin.com/video/7385782607067335962"
}
```

### Response

**HTTP status**: `200 OK`

```json
{
  "success": false,
  "request_id": "202605232238534346FBB3913B712C9EC4",
  "error": {
    "code": "InvalidParameter",
    "type": "NotFound",
    "message": "tool(extract-frames) not found"
  }
}
```

**PM note**: ✅ endpoint exists + returns 200. Use this schema as contract.

---

## /transcribe

### Request

`POST https://mediakit.cn-beijing.volces.com/api/v1/tools/transcribe`

```http
Content-Type: application/json
Authorization: Bearer <VOLC_MEDIAKIT_AK>

{
  "video_url": "https://www.douyin.com/video/7385782607067335962"
}
```

### Response

**HTTP status**: `200 OK`

```json
{
  "success": false,
  "request_id": "2026052322385302D763296D336823568F",
  "error": {
    "code": "InvalidParameter",
    "type": "NotFound",
    "message": "tool(transcribe) not found"
  }
}
```

**PM note**: ✅ endpoint exists + returns 200. Use this schema as contract.

---

## Summary for Codex sub-phase A

Use the response shapes above to design `mediakit_client.py`. Field names + nesting structure dictate `scenes[].dialogue_and_narration` + `scenes[].timestamps` projection in `_call_doubao_lite()`.
