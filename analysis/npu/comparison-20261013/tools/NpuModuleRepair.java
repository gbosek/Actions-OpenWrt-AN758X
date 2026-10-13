// Repair inferred callback boundaries in an analysis database, not input bytes.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class NpuModuleRepair extends GhidraScript {
    public void run() throws Exception {
        Address csr = toAddr(0x100000L);
        if (getFunctionAt(csr) == null) {
            disassemble(csr);
            createFunction(csr, "proc_core_csr_write_inferred");
        }
        // .rela.rodata points to .text+0x5e0. ARM64 PACIASP is its first
        // instruction; .text+0x5e4 is an interior STP, not another callback.
        currentProgram.getFunctionManager().removeFunction(toAddr(0x1005e4L));
        Address mapping = toAddr(0x1005e0L);
        Function f = getFunctionAt(mapping);
        if (f == null) f = createFunction(mapping, "proc_mapping_write_inferred");
        if (f != null) {
            f.setBody(new AddressSet(mapping, toAddr(0x1005ffL)));
            f.setName("proc_mapping_write_inferred", SourceType.ANALYSIS);
        }
        analyzeChanges(currentProgram);
        println("Callback boundaries reconciled with original ELF relocations and ARM64 instructions.");
    }
}
