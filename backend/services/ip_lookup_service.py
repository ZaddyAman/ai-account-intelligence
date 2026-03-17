"""IP lookup service using ip-api.com (free, no key needed)."""

import httpx


async def lookup_ip(ip_address: str) -> dict:
    """Look up an IP address and return geolocation + org info.
    
    Returns dict with keys: org, isp, city, region, country, lat, lon, etc.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,message,country,regionName,city,lat,lon,isp,org,as,query"},
            )
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "org": data.get("org", ""),
                    "isp": data.get("isp", ""),
                    "city": data.get("city", ""),
                    "region": data.get("regionName", ""),
                    "country": data.get("country", ""),
                    "lat": data.get("lat", 0),
                    "lon": data.get("lon", 0),
                    "as_number": data.get("as", ""),
                    "success": True,
                }
    except Exception as e:
        print(f"[IP LOOKUP ERROR] {ip_address}: {e}")
    return {"org": "", "isp": "", "city": "", "region": "", "country": "", "success": False}
