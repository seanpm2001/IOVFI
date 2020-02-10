import logging
import os
import pickle

import numpy
from sklearn import tree, preprocessing

from .FBLogging import logger
from .PinRun import PinMessage, PinRun


class FBDecisionTree:
    UNKNOWN_FUNC = -1
    WATCHDOG = 1.0
    MAX_CONFIRM = 1

    def _log(self, msg, level=logging.INFO):
        logger.log(level, msg)

    def _find_dtree_idx(self, index):
        if index < 0:
            raise ValueError("Invalid dtree index: {}".format(index))

        for base_idx, dtree in self.dtrees.items():
            if index < base_idx:
                continue

            if index - base_idx < dtree.tree_.node_count:
                return base_idx
        raise ValueError("Could not find dtree corresponding to index {}".format(index))

    def _left_child(self, index):
        return self._child(index, False)

    def _right_child(self, index):
        return self._child(index, True)

    def _is_leaf(self, index):
        if index < 0:
            return True

        return self._left_child(index) == self._right_child(index)

    def _attempt_ctx(self, iovec, pin_run, watchdog=WATCHDOG):
        if iovec is None:
            raise AssertionError("No iovec provided")
        elif pin_run is None:
            raise AssertionError("pin_run cannot be None")
        elif not pin_run.is_running():
            raise AssertionError("pin_run is not running")

        ack_msg = pin_run.send_reset_cmd(watchdog)
        if ack_msg is None or ack_msg.msgtype != PinMessage.ZMSG_ACK:
            raise AssertionError("Received no ack for set context cmd")
        resp_msg = pin_run.read_response(watchdog)
        if resp_msg is None or resp_msg.msgtype != PinMessage.ZMSG_OK:
            raise AssertionError("Set context command failed")

        ack_msg = pin_run.send_set_ctx_cmd(iovec, watchdog)
        if ack_msg is None or ack_msg.msgtype != PinMessage.ZMSG_ACK:
            raise AssertionError("Received no ack for set context cmd")
        resp_msg = pin_run.read_response(watchdog)
        if resp_msg is None or resp_msg.msgtype != PinMessage.ZMSG_OK:
            raise AssertionError("Set context command failed")

        ack_msg = pin_run.send_execute_cmd(watchdog)
        if ack_msg is None or ack_msg.msgtype != PinMessage.ZMSG_ACK:
            raise AssertionError("Received no ack for execute cmd")
        resp_msg = pin_run.read_response(watchdog)
        if resp_msg is None:
            raise AssertionError("Execute command did not return")
        return resp_msg.msgtype == PinMessage.ZMSG_OK

    def _child(self, index, right_child):
        if index < 0:
            raise ValueError("Invalid index: {}".format(index))

        if index in self.child_dtrees:
            return self.child_dtrees[index]

        dtree_idx = self._find_dtree_idx(index)
        dtree = self.dtrees[dtree_idx]
        tree_idx = index - dtree_idx

        if right_child:
            child_idx = dtree.tree_.children_right[tree_idx]
        else:
            child_idx = dtree.tree_.children_left[tree_idx]

        if child_idx < 0:
            return child_idx

        return dtree_idx + child_idx

    def export_graphviz(self, outfile, treeidx=0):
        dtree = self.dtrees[treeidx]
        tree.export_graphviz(dtree, out_file=outfile, filled=True, rounded=True, special_characters=True,
                             node_ids=True, label='none')

    def get_func_descs(self):
        results = set()
        for hashsum, func_desc in self.funcDescs.items():
            results.add(func_desc)

        return results

    def get_all_equiv_classes(self):
        result = list()
        for idx in range(0, self.size()):
            if self._is_leaf(idx):
                result.append(self.get_equiv_classes(idx))
        return result

    def get_equiv_classes(self, index):
        if index == self.UNKNOWN_FUNC:
            return None

        if not self._is_leaf(index):
            raise ValueError("Node {} is not a leaf".format(index))

        dtree_idx = self._find_dtree_idx(index)
        dtree = self.dtrees[dtree_idx]
        tree_idx = index - dtree_idx
        equiv_classes = set()
        for i in range(len(dtree.tree_.value[tree_idx][0])):
            if dtree.tree_.value[tree_idx][0][i]:
                hash_sum = dtree.classes_[i]
                equiv_classes.add(self.funcDescs[hash_sum])

        return equiv_classes

    def _confirm_leaf(self, func_desc, index, pin_run, max_iovecs=MAX_CONFIRM):
        possible_equivs = self.get_equiv_classes(index)
        equiv_class_names = set()
        for ec in possible_equivs:
            equiv_class_names.add(ec.name)

        try:
            self._log("Confirming {}({}) is {}".format(func_desc.name, hex(func_desc.location),
                                                       " ".join(equiv_class_names)))
            if not self._is_leaf(index):
                raise AssertionError("{} is not a leaf".format(index))

            dtree_base_idx = self._find_dtree_idx(index)
            dtree = self.dtrees[dtree_base_idx]
            descMap = self.descMaps[dtree_base_idx]
            hashMap = self.hashMaps[dtree_base_idx]
            labels = self.labels[dtree_base_idx]

            lengths = list()
            for hash_sum, accepting_funcs in descMap.items():
                for possible_equiv in possible_equivs:
                    if possible_equiv in accepting_funcs:
                        lengths.append((hash_sum, len(accepting_funcs)))
                        continue

            sorted_iovecs = sorted(lengths, key=lambda length: length[1])
            for hash_sum in sorted_iovecs[0:min(len(sorted_iovecs), max_iovecs)]:
                # hash_sum = available_hashes[0]
                iovec = hashMap[hash_sum[0]]
                print("Using iovec {}".format(iovec.hexdigest()))
                if not self._attempt_ctx(iovec, pin_run):
                    return False

            return True
        except Exception as e:
            logger.exception(e)
            raise e

    def _get_hash(self, index):
        base_dtree_index = self._find_dtree_idx(index)
        tree_idx = index - base_dtree_index
        dtree = self.dtrees[base_dtree_index]
        hash = self.labels[base_dtree_index].inverse_transform([dtree.tree_.feature[tree_idx]])[0]
        return hash

    def get_iovec(self, index):
        try:
            if index < 0:
                return None
            hash = self._get_hash(index)
            base_dtree_index = self._find_dtree_idx(index)
            if hash in self.hashMaps[base_dtree_index]:
                return self.hashMaps[base_dtree_index][hash]
            return None
        except:
            return None

    def identify(self, func_desc, pin_loc, pintool_loc, loader_loc=None, cwd=os.getcwd(), max_confirm=MAX_CONFIRM,
                 rust_main=None):
        pin_run = PinRun(pin_loc, pintool_loc, func_desc.binary, loader_loc, cwd=cwd, rust_main=rust_main)

        idx = 0
        try:
            while idx < self.size():
                if not pin_run.is_running():
                    pin_run.stop()
                    pin_run.start(timeout=FBDecisionTree.WATCHDOG)
                    if pin_run.rust_main is None:
                        if loader_loc is None:
                            ack_msg = pin_run.send_set_target_cmd(func_desc.location, FBDecisionTree.WATCHDOG)
                        else:
                            ack_msg = pin_run.send_set_target_cmd(func_desc.name, FBDecisionTree.WATCHDOG)
                    else:
                        ack_msg = pin_run.send_set_target_cmd(func_desc.name, FBDecisionTree.WATCHDOG)

                    if ack_msg is None or ack_msg.msgtype != PinMessage.ZMSG_ACK:
                        raise AssertionError("Could not set target for {}".format(str(func_desc)))
                    resp_msg = pin_run.read_response(FBDecisionTree.WATCHDOG)
                    if resp_msg is None or resp_msg.msgtype != PinMessage.ZMSG_OK:
                        raise AssertionError("Could not set target for {}".format(str(func_desc)))

                if self._is_leaf(idx):
                    try:
                        if self._confirm_leaf(func_desc, idx, pin_run, max_confirm):
                            pin_run.stop()
                            return idx
                        break
                    except RuntimeError as e:
                        # No available hashes, so just mark the identified leaf
                        # as the identified leaf
                        pin_run.stop()
                        return idx
                    except Exception as e:
                        logger.exception("Error confirming leaf for {}: {}".format(func_desc, e))
                        break

                iovec = self.get_iovec(idx)
                iovec_accepted = False
                try:
                    logger.debug("Trying iovec {} ({})".format(idx, iovec.hexdigest()))
                    iovec_accepted = self._attempt_ctx(iovec, pin_run)
                except Exception as e:
                    logger.exception("Error testing iovec for {}: {}".format(str(func_desc), e))

                if iovec_accepted:
                    idx = self._right_child(idx)
                else:
                    idx = self._left_child(idx)

            pin_run.stop()
            return self.UNKNOWN_FUNC
        except Exception as e:
            pin_run.stop()
            raise e

    def size(self):
        size = 0
        for dtree in self.dtrees.values():
            size += dtree.tree_.node_count

        return size

    def __sizeof__(self):
        return self.size()

    def add_dtree(self, descLoc, hashMapLoc):
        if not os.path.exists(descLoc):
            raise FileNotFoundError(descLoc)
        if not os.path.exists(hashMapLoc):
            raise FileNotFoundError(hashMapLoc)

        base_idx = 0
        for dtree in self.dtrees.items():
            base_idx += dtree.tree_.node_count
        self._log("base_idx = {}".format(base_idx))

        msg = "Loading {}...".format(descLoc)
        with open(descLoc, "rb") as descFile:
            self.descMaps[base_idx] = pickle.load(descFile)
        for key, funcDescs in self.descMaps[base_idx].items():
            for (funcDesc, coverage) in funcDescs:
                # print("{}: {}".format(funcDesc.name, coverage))
                self.funcDescs[hash(funcDesc)] = (funcDesc, coverage)
        self._log(msg + "done!")

        msg = "Loading {}...".format(hashMapLoc)
        with open(hashMapLoc, "rb") as hashMapFile:
            self.hashMaps[base_idx] = pickle.load(hashMapFile)
        self._log(msg + "done!")

        labels = preprocessing.LabelEncoder()
        hash_labels = set()
        msg = "Transforming function labels..."
        for hashes in self.descMaps[base_idx].keys():
            hash_labels.add(hashes)
        labels.fit_transform(list(hash_labels))
        self.labels[base_idx] = labels
        self._log(msg + "done!")

        funcs_labels = list()
        funcs_features = list()
        added_func_hashes = set()

        msg = "Reading in function labels..."
        count = 0
        for key, funcs in self.descMaps[base_idx].items():
            idx = self.labels[base_idx].transform([key])[0]
            count += 1
            for (func, coverage) in funcs:
                hashsum = hash(func)
                if hashsum not in added_func_hashes:
                    added_func_hashes.add(hashsum)
                    funcs_labels.append(hashsum)
                    funcs_features.append(numpy.zeros(len(self.labels[base_idx].classes_), dtype=bool))
                func_feature = funcs_features[funcs_labels.index(hashsum)]
                func_feature[idx] = True
        self._log(msg + "done!")

        dtree = tree.DecisionTreeClassifier()
        msg = "Creating decision tree..."
        dtree.fit(funcs_features, funcs_labels)
        self.dtrees[base_idx] = dtree
        self._log(msg + "done!")

    def __init__(self, descLoc, hashMapLoc):
        # Map of base index to dtree
        self.dtrees = dict()
        # Map of Whole Tree Index to Child Subtree Whole Tree Index
        self.child_dtrees = dict()
        # Map of Whole Tree Index to Corresponding Labels
        self.labels = dict()
        # Map of Whole Tree Index to Corresponding Descriptors
        self.descMaps = dict()
        # Map of Whole Tree Index to Corresponding Hash Maps
        self.hashMaps = dict()
        # Map of all function hashes to FunctionDescriptors
        self.funcDescs = dict()

        self.add_dtree(descLoc, hashMapLoc)
