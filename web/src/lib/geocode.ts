// postcodes.io lookup (public, no key). Returns null when the lookup fails.

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
