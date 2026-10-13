
bool ppe_check_start_to_bind(long param_1,uint *param_2)

{
  byte bVar1;
  uint uVar2;
  uint uVar3;
  ushort uVar4;
  int iVar5;
  uint uVar6;
  
  uVar4 = *(ushort *)(param_1 + 0xcc);
  uVar6 = (uint)uVar4;
  if (ppeSupportPreBind == 0) {
    if (uVar4 != 0x7280 && uVar4 != 0x7275) {
      uVar2 = uVar6 - 0x7274 & 0xffff;
      uVar3 = (uint)(uVar6 == 0x7615) | (uint)(0xfa63dfe7f9 >> ((ulong)uVar2 & 0x3f)) & 1;
      if (0x27 < uVar2) {
        uVar3 = (uint)(uVar6 == 0x7615);
      }
      if (uVar3 == 0) {
        return false;
      }
    }
    if ((*(byte *)(param_1 + 0xd0) & 0x1f) != 0xf) {
      iVar5 = ppeCheckFastRuleBind(param_1);
      return iVar5 != 0;
    }
    return true;
  }
  if (uVar4 != 0x7280 && uVar4 != 0x7275) {
    uVar2 = uVar6 - 0x7274 & 0xffff;
    uVar3 = (uint)(uVar6 == 0x7615) | (uint)(0xfa63dfe7f9 >> ((ulong)uVar2 & 0x3f)) & 1;
    if (0x27 < uVar2) {
      uVar3 = (uint)(uVar6 == 0x7615);
    }
    if (uVar3 == 0) {
      return false;
    }
  }
  bVar1 = *(byte *)(param_1 + 0xd0) & 0x1f;
  if (bVar1 != 0xf) {
    return bVar1 == 0x1a;
  }
  *param_2 = *param_2 | 0x1000000;
  return false;
}

