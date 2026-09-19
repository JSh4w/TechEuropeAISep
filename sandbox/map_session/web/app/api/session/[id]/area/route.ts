import { UPDATE_SUBMIT_AREA, errorResponse, temporal } from "@/lib/temporal";
import type { AreaFeedback, Polygon } from "@/lib/types";

/** The human edited the area on the map. Returns validation feedback, or 400 if the workflow rejected the edit. */
export async function POST(req: Request, ctx: RouteContext<"/api/session/[id]/area">) {
  const { id } = await ctx.params;
  const area = (await req.json()) as Polygon;
  try {
    const client = await temporal();
    const feedback = await client.workflow
      .getHandle(id)
      .executeUpdate<AreaFeedback, [Polygon]>(UPDATE_SUBMIT_AREA, { args: [area] });
    return Response.json(feedback);
  } catch (err) {
    return errorResponse(err);
  }
}
