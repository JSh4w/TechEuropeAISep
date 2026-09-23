// postcodes.io lookups (public, no key). Both return null when the lookup fails.

/** [lon, lat] for a UK postcode. */
export async function geocodePostcode(postcode: string): Promise<[number, number] | null> {
  try {
    const r = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(postcode)}`);
    const data = await r.json();
    if (data?.status === 200 && data.result?.longitude && data.result?.latitude) {
      return [data.result.longitude, data.result.latitude];
    }
  } catch {
    // fall through
  }
  return null;
}

/** The postcode nearest to a [lon, lat] point, within 2 km. */
export async function nearestPostcode([lon, lat]: [number, number]): Promise<string | null> {
  try {
    const r = await fetch(
      `https://api.postcodes.io/postcodes?lon=${lon}&lat=${lat}&limit=1&radius=2000&widesearch=true`
    );
    return ((await r.json())?.result?.[0]?.postcode as string | undefined) ?? null;
  } catch {
    return null;
  }
}
