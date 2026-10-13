// Supplemental direct-Ghidra output; this is not an REA Evidence envelope.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Reference;
import java.io.PrintWriter;

public class NpuDump extends GhidraScript {
    private String quote(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\\' || c == '"') b.append('\\').append(c);
            else if (c == '\n') b.append("\\n");
            else if (c == '\r') b.append("\\r");
            else if (c == '\t') b.append("\\t");
            else if (c < 32) b.append(String.format("\\u%04x", (int)c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(getScriptArgs()[0])) {
            out.println("{\"provider\":\"direct-ghidra-12.1.4\",\"code_base\":\"0x84000000\",\"data_base\":\"0x3e900000\",\"language\":" + quote(currentProgram.getLanguageID().toString()) + ",\"functions\":[");
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            boolean first = true;
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function f = functions.next();
                if (f.isExternal()) continue;
                DecompileResults r = decomp.decompileFunction(f, 15, monitor);
                if (!first) out.println(",");
                first = false;
                out.print("{\"address\":" + quote("0x" + Long.toHexString(f.getEntryPoint().getOffset())) + ",\"name\":" + quote(f.getName()) + ",\"size\":" + f.getBody().getNumAddresses() + ",\"decompiled\":" + r.decompileCompleted() + ",\"pseudocode\":" + quote(r.getDecompiledFunction() == null ? null : r.getDecompiledFunction().getC()) + ",\"references\":[");
                ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
                boolean refFirst = true;
                while (refs.hasNext()) {
                    Reference ref = refs.next();
                    if (!refFirst) out.print(",");
                    refFirst = false;
                    out.print("{\"source\":" + quote("0x" + Long.toHexString(ref.getFromAddress().getOffset())) + ",\"type\":" + quote(ref.getReferenceType().toString()) + "}");
                }
                out.print("]}");
            }
            out.println("]}");
        } finally {
            decomp.dispose();
        }
    }
}
