
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void PpeSetEntryBind(long param_1,uint *param_2)

{
  uint uVar1;
  undefined2 uVar2;
  ushort uVar3;
  int iVar4;
  uint *puVar5;
  uint local_20;
  undefined4 local_1c;
  undefined8 local_18;
  undefined8 uStack_10;
  undefined8 local_8;
  
  puVar5 = param_2 + 4;
  local_1c = *param_2;
  uVar2 = *(undefined2 *)(param_1 + 0xce);
  uVar1 = local_1c & 0xe000000;
  if ((local_1c & 0xc000000) != 0 && uVar1 != 0x6000000) {
    if (uVar1 == 0xe000000 || (local_1c & 0xc000000) == 0x8000000) {
      puVar5 = param_2 + 0xb;
    }
    else {
      if (uVar1 != 0x4000000) {
        return;
      }
      puVar5 = param_2 + 0xb;
    }
  }
  FUN_0013a930(&local_20);
  if ((*(char *)(param_1 + 0xda) == '\x01') || ((*puVar5 & 0x1e0) == 0x1e0)) {
    local_1c = local_1c & 0xfeff8000 | local_20 & 0x7fff;
  }
  else {
    local_1c = local_1c & 0xffff8000 | local_20 & 0x7fff | 0x1000000;
  }
  uStack_10 = 0;
  local_18 = 4;
  local_8 = 0xffffffff;
  iVar4 = __ECNT_HOOK(0x47,0,&local_18);
  if ((iVar4 != -1) && (-1 < (int)local_8)) {
    local_1c = local_1c & 0xfeffffff;
  }
  uVar3 = (ushort)(((uint)((ulong)DAT_00193e08 >> 0x20) & 1) << 7) | 0x2000 |
          local_1c._2_2_ & 0xcf7f;
  if ((DAT_00193ea8 & 1) == 0) {
    local_1c = (uVar3 & 0xfff0) << 0x10 | local_1c & 0xffff | (DAT_00193d9e & 0xf) << 0x10;
    iVar4 = DAT_00193da0;
  }
  else {
    local_1c = (uVar3 & 0xfff0) << 0x10 | local_1c & 0xffff | (DAT_00193e38 & 0xf) << 0x10;
    iVar4 = DAT_00193e3c;
  }
  if (iVar4 == 0) {
    local_1c = local_1c & 0xffbfffff;
  }
  else {
    local_1c = local_1c | 0x400000;
  }
  iVar4 = GET_HIR();
  if ((iVar4 != 10) && (iVar4 = GET_HIR(), iVar4 != 0xc)) {
    GET_HIR();
  }
  iVar4 = ppe_is_multicast_entry(param_2);
  if (((iVar4 != 0) && (iVar4 = GET_HIR(), iVar4 != 10)) && (iVar4 = GET_HIR(), iVar4 != 0xc)) {
    GET_HIR();
  }
  ecnt_ppe_set_entry_bind_hook(param_1,param_2,&local_1c);
  *param_2 = local_1c;
  if ((local_1c & 0xc000000) == 0 || (local_1c & 0xe000000) == 0x6000000) {
    if (DAT_00193ec0 == 1) {
      if ((_hwnat_bind_entry_info_fn != (undefined8 *)0x0) &&
         ((code *)*_hwnat_bind_entry_info_fn != (code *)0x0)) {
        (*(code *)*_hwnat_bind_entry_info_fn)
                  (uVar2,param_2[1],param_2[2],*(undefined2 *)((long)param_2 + 0xe),
                   (short)param_2[3],DAT_00193db5);
      }
    }
    else if ((_hwnat_bind_entry_info_fn != (undefined8 *)0x0) &&
            ((code *)*_hwnat_bind_entry_info_fn != (code *)0x0)) {
      (*(code *)*_hwnat_bind_entry_info_fn)
                (uVar2,param_2[5],param_2[6],*(undefined2 *)((long)param_2 + 0x1e),(short)param_2[7]
                 ,DAT_00193db5);
    }
  }
  else if ((((local_1c & 0xe000000) == 0xe000000 || (local_1c & 0xc000000) == 0x8000000) &&
           (_hwnat_bind_entry_info_fn != (undefined8 *)0x0)) &&
          ((code *)_hwnat_bind_entry_info_fn[1] != (code *)0x0)) {
    (*(code *)_hwnat_bind_entry_info_fn[1])
              (uVar2,param_2[1],param_2[2],param_2[3],param_2[4],param_2[5],param_2[6],param_2[7],
               param_2[8],*(undefined2 *)((long)param_2 + 0x26),(short)param_2[9],DAT_00193dc0._6_1_
              );
    return;
  }
  return;
}

