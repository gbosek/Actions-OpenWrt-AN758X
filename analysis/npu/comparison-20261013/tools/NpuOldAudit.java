// Supplemental, scoped direct Ghidra audit; not an REA Evidence envelope.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import java.io.PrintWriter;

public class NpuOldAudit extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface di = new DecompInterface();
        for (int i = 1; i < args.length; i++) {
            Address address = toAddr(Long.parseUnsignedLong(args[i].replace("0x", ""), 16));
            if (getFunctionAt(address) == null && getFunctionContaining(address) == null) {
                disassemble(address);
                createFunction(address, "audit_" + args[i].replace("0x", ""));
            }
        }
        analyzeChanges(currentProgram);
        di.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0])) {
            out.println("Supplemental direct-ghidra-12.1.4 scoped old firmware audit.");
            for (int i = 1; i < args.length; i++) {
                Address address = toAddr(Long.parseUnsignedLong(args[i].replace("0x", ""), 16));
                out.println("\n=== Requested " + address + " ===");
                Function f = getFunctionContaining(address);
                if (f == null) { out.println("No function recovered"); continue; }
                out.println("Function " + f.getEntryPoint() + " body " + f.getBody());
                for (Reference ref : getReferencesTo(address)) out.println("REF " + ref.getFromAddress() + " " + ref.getReferenceType());
                InstructionIterator ins = currentProgram.getListing().getInstructions(f.getBody(), true);
                while (ins.hasNext()) {
                    Instruction inst = ins.next();
                    out.println(inst.getAddress() + " " + inst.toString());
                }
                DecompileResults r = di.decompileFunction(f, 30, monitor);
                out.println("Decompile completed=" + r.decompileCompleted() + " error=" + r.getErrorMessage());
                if (r.getDecompiledFunction() != null) out.println(r.getDecompiledFunction().getC());
            }
            out.println("\n=== Static references to callback-table storage and FE / QDMA / NPU-bridge MMIO ===");
            long tableBase = currentProgram.getName().startsWith("1-naoki") ? 0x3e900aa8L : 0x3e900bd0L;
            InstructionIterator all = currentProgram.getListing().getInstructions(true);
            while (all.hasNext()) {
                Instruction inst = all.next();
                for (Reference ref : inst.getReferencesFrom()) {
                    long value = ref.getToAddress().getOffset();
                    boolean callbacks = value >= tableBase && value < tableBase + 0x280;
                    boolean fe = value >= 0x1fb50000L && value < 0x1fb58000L;
                    boolean bridge = value >= 0x1ec12000L && value < 0x1ec12400L;
                    boolean host = value >= 0x1ec0d000L && value < 0x1ec0d200L;
                    if (callbacks || fe || bridge || host)
                        out.println("REF " + inst.getAddress() + " -> " + ref.getToAddress() + " " + ref.getReferenceType() + " : " + inst);
                }
            }
        } finally { di.dispose(); }
    }
}
