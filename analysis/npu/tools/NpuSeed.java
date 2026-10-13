// Seed candidate function entries from the supplied .data pointer words.
// Candidate discovery is not a recovered original symbol table.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import java.math.BigInteger;

public class NpuSeed extends GhidraScript {
    public void run() throws Exception {
        MemoryBlock data = currentProgram.getMemory().getBlock("npu_data");
        MemoryBlock code = currentProgram.getMemory().getBlock(toAddr(0x84000000L));
        if (getScriptArgs().length > 0) {
            currentProgram.getProgramContext().setValue(
                currentProgram.getRegister("gp"), code.getStart(), code.getEnd(),
                new BigInteger(getScriptArgs()[0].replace("0x", ""), 16));
        }
        int count = 0;
        for (long off = 0; off + 4 <= data.getSize(); off += 4) {
            long value = Integer.toUnsignedLong(currentProgram.getMemory().getInt(data.getStart().add(off)));
            if (value < 0x84000000L || value > code.getEnd().getOffset() || (value & 1) != 0) continue;
            Address address = toAddr(value);
            if (getFunctionContaining(address) != null || getDataContaining(address) != null) continue;
            if (disassemble(address) && createFunction(address, null) != null) count++;
        }
        println("Seeded " + count + " candidate functions from npu_data pointers");
    }
}
