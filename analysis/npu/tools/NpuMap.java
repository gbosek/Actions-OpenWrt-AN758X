// Analysis-only map for the user-supplied AN7581 RV32 raw images.
// The supplied code and data are never modified.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.MemoryBlock;
import java.io.File;
import java.io.FileInputStream;

public class NpuMap extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        MemoryBlock code = currentProgram.getMemory().getBlock(toAddr(0x84000000L));
        code.setExecute(true);
        code.setWrite(false);
        File data = new File(args[0]);
        try (FileInputStream in = new FileInputStream(data)) {
            MemoryBlock sram = currentProgram.getMemory().createInitializedBlock(
                "npu_data", toAddr(0x3e900000L), in, data.length(), monitor, false);
            sram.setRead(true);
            sram.setWrite(true);
        }
        MemoryBlock bss = currentProgram.getMemory().createUninitializedBlock(
            "npu_sram_remaining", toAddr(0x3e900000L + data.length()),
            0x10000L - data.length(), false);
        bss.setRead(true);
        bss.setWrite(true);
        disassemble(toAddr(0x84000000L));
        createFunction(toAddr(0x84000000L), "raw_entry");
    }
}
