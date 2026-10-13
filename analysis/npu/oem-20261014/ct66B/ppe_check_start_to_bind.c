
bool ppe_check_start_to_bind(long param_1,uint *param_2)

{
  ushort uVar1;
  int iVar2;
  uint uVar3;
  
  uVar1 = *(ushort *)(param_1 + 0x12d);
  uVar3 = (uint)uVar1;
  if (ppeSupportPreBind == 0) {
    if (uVar3 < 0x72a4) {
      if (uVar3 < 0x7274) {
        return false;
      }
      if (((0xdffb63dff7fbU >> ((ulong)(uVar3 - 0x7274) & 0x3f) & 1) != 0) &&
         ((*(byte *)(param_1 + 0x131) & 0x1f) == 0xf)) {
        return true;
      }
      if ((0xdffb63dff7fbU >> ((ulong)(uVar3 - 0x7274) & 0x3f) & 1) == 0) {
        return false;
      }
    }
    else {
      if (uVar3 != 0x7615) {
        return false;
      }
      if ((*(byte *)(param_1 + 0x131) & 0x1f) == 0xf) {
        return true;
      }
    }
    iVar2 = ppeCheckFastRuleBind(param_1);
    return iVar2 != 0;
  }
  if (uVar1 < 0x72a4) {
    if (uVar1 < 0x7274) {
      return false;
    }
    if (((0xdffb63dff7fbU >> ((ulong)(uVar3 - 0x7274) & 0x3f) & 1) == 0) ||
       ((*(byte *)(param_1 + 0x131) & 0x1f) != 0xf)) {
      if ((0xdffb63dff7fbU >> ((ulong)(uVar3 - 0x7274) & 0x3f) & 1) == 0) {
        return false;
      }
LAB_0015a2b4:
      return (*(byte *)(param_1 + 0x131) & 0x1f) == 0x1a;
    }
  }
  else {
    if (uVar1 != 0x7615) {
      return false;
    }
    if ((*(byte *)(param_1 + 0x131) & 0x1f) != 0xf) goto LAB_0015a2b4;
  }
  *param_2 = *param_2 | 0x1000000;
  return false;
}

