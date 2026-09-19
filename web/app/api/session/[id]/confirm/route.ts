import { UPDATE_CONFIRM_AREA, errorResponse, temporal } from "@/lib/temporal";
import type { SessionState } from "@/lib/types";

/** The human accepts the current area; the workflow moves on to the engines. */
export async function POST(_req: Request, ctx: RouteContext<"/api/session/[id]/confirm">) {
  const { id } = await ctx.params;
  try {
    const client = await temporal();
    const state = await client.workflow.getHandle(id).executeUpdate<SessionState, []>(UPDATE_CONFIRM_AREA);
    return Response.json(state);
  } catch (err) {
    return errorResponse(err);
  }
}
