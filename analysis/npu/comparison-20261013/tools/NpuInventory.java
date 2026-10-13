// Supplemental direct Ghidra inventory. Original input bytes are unchanged.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.address.AddressRangeIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.PrintWriter;

public class NpuInventory extends GhidraScript {
    private String hex(Address address) {
        return "0x" + Long.toHexString(address.getOffset());
    }
    public void run() throws Exception {
        String[] args = getScriptArgs();
        JsonArray requested = new JsonArray();
        for (int i = 1; i < args.length; i++) {
            Address a = toAddr(Long.parseUnsignedLong(args[i].replace("0x", ""), 16));
            if (getFunctionAt(a) == null && getFunctionContaining(a) == null) {
                disassemble(a);
                createFunction(a, "audited_" + args[i].replace("0x", ""));
            }
            JsonObject item = new JsonObject();
            item.addProperty("requested", hex(a));
            Function f = getFunctionContaining(a);
            if (f != null) item.addProperty("recovered_entry", hex(f.getEntryPoint()));
            requested.add(item);
        }
        analyzeChanges(currentProgram);
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        JsonObject output = new JsonObject();
        output.addProperty("provider", "direct-ghidra-12.1.4");
        output.addProperty("program", currentProgram.getName());
        output.addProperty("language", currentProgram.getLanguageID().toString());
        output.addProperty("coverage_note", "All current analyzer candidate functions and decoded instructions; not a proof of exhaustive code discovery or correct semantics.");
        output.add("requested_entries", requested);
        JsonArray functions = new JsonArray();
        FunctionIterator iterator = currentProgram.getFunctionManager().getFunctions(true);
        while (iterator.hasNext() && !monitor.isCancelled()) {
            Function f = iterator.next();
            JsonObject item = new JsonObject();
            item.addProperty("address", hex(f.getEntryPoint()));
            item.addProperty("name", f.getName());
            item.addProperty("external", f.isExternal());
            item.addProperty("thunk", f.isThunk());
            item.addProperty("body_bytes", f.getBody().getNumAddresses());
            JsonArray ranges = new JsonArray();
            AddressRangeIterator ri = f.getBody().getAddressRanges();
            while (ri.hasNext()) {
                AddressRange range = ri.next();
                JsonObject r = new JsonObject();
                r.addProperty("start", hex(range.getMinAddress()));
                r.addProperty("end_inclusive", hex(range.getMaxAddress()));
                ranges.add(r);
            }
            item.add("body_ranges", ranges);
            if (!f.isExternal() && !f.isThunk()) {
                DecompileResults result = di.decompileFunction(f, 30, monitor);
                item.addProperty("decompiled", result.decompileCompleted());
                item.addProperty("error_message", result.getErrorMessage());
                if (result.getDecompiledFunction() != null)
                    item.addProperty("pseudocode", result.getDecompiledFunction().getC());
            }
            JsonArray incoming = new JsonArray();
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
            while (refs.hasNext()) {
                Reference ref = refs.next();
                JsonObject r = new JsonObject();
                r.addProperty("source", hex(ref.getFromAddress()));
                r.addProperty("type", ref.getReferenceType().toString());
                incoming.add(r);
            }
            item.add("incoming", incoming);
            functions.add(item);
        }
        output.add("functions", functions);
        JsonArray instructions = new JsonArray();
        InstructionIterator ii = currentProgram.getListing().getInstructions(true);
        while (ii.hasNext()) {
            Instruction inst = ii.next();
            JsonObject item = new JsonObject();
            item.addProperty("address", hex(inst.getAddress()));
            item.addProperty("length", inst.getLength());
            item.addProperty("assembly", inst.toString());
            JsonArray references = new JsonArray();
            for (Reference ref : inst.getReferencesFrom()) {
                JsonObject r = new JsonObject();
                r.addProperty("to", hex(ref.getToAddress()));
                r.addProperty("type", ref.getReferenceType().toString());
                references.add(r);
            }
            item.add("references", references);
            instructions.add(item);
        }
        output.add("decoded_instructions", instructions);
        try (PrintWriter out = new PrintWriter(args[0])) {
            out.println(new GsonBuilder().setPrettyPrinting().create().toJson(output));
        } finally { di.dispose(); }
    }
}
